from xml.etree import ElementTree as ET
import xml.dom.minidom as minidom
import utils


class WitnessCreator(object):

    def __init__(self):
        self._node_id_counter = -1

    def _create_witness_header(self, filename):
        graphml = ET.Element('graphml')
        graphml.set('xmlns', 'http://graphml.graphdrawing.org/xmlns')
        graphml.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')

        key = ET.SubElement(graphml, 'key')
        key.set('attr.name', 'originFileName')
        key.set('attr.type', 'string')
        key.set('for', 'edge')
        key.set('id', 'originfile')
        default_key = ET.SubElement(key, 'default')
        default_key.text = filename

        return graphml

    def _create_data_element(self, keyname, text):
        data_el = ET.Element('data')
        data_el.text = str(text)
        data_el.set('key', str(keyname))
        return data_el

    def _next_node_id(self):
        self._node_id_counter += 1
        return 'A' + str(self._node_id_counter)

    def _create_node(self, entry=False, violation=False):
        node = ET.Element('node')
        node.set('id', self._next_node_id())
        if entry:
            node.append(self._create_data_element('entry', 'true'))
        if violation:
            node.append(self._create_data_element('violation', 'true'))
        return node

    def _reset_node_id(self):
        self._node_id_counter = -1

    def _create_edge(self, source, target, assumption=None, startline=None, assumption_scope=None):
        edge = ET.Element('edge')
        edge.set('source', source)
        edge.set('target', target)
        if startline:
            edge.append(self._create_data_element('startline', startline))
        if assumption:
            edge.append(self._create_data_element('assumption', assumption))
        if assumption_scope:
            edge.append(self._create_data_element('assumption.scope', assumption_scope))

        return edge

    def _create_graph_head(self, producer, filename, machine_model):
        graph = ET.Element('graph')
        graph.set('edgedefault', 'directed')

        # Create data elements that describe witness
        graph.append(self._create_data_element('witness-type', 'violation_witness'))
        graph.append(self._create_data_element('sourcecodelang', 'C'))
        graph.append(self._create_data_element('producer', producer))
        graph.append(self._create_data_element('specification', 'CHECK( init(main()), LTL(G ! call(__VERIFIER_error())) )'))
        #graph.append(self._create_data_element('testfile', test_file))
        #timestamp = utils.get_time()
        #graph.append(self._create_data_element('creationtime', timestamp))
        graph.append(self._create_data_element('programfile', filename))
        filehash = utils.get_hash(filename)
        graph.append(self._create_data_element('programhash', filehash))
        graph.append(self._create_data_element('architecture', machine_model))

        return graph

    def _create_automaton(self, graph, test_vector, nondet_methods, error_lines):
        # Create entry node
        previous_node = self._create_node(entry=True)

        graph.append(previous_node)

        for num, instantiation in enumerate(test_vector.vector):
            target_node = self._create_node()
            graph.append(target_node)
            if instantiation['name']:
                possible_methods = [instantiation['name']]
            else:
                possible_methods = sorted(nondet_methods)  # Sort just so the witness always looks the same

            for nondet_method in possible_methods:
                assumption = '\\result == ' + instantiation['value'] + ';'
                new_edge = self._create_edge(previous_node.get('id'), target_node.get('id'), assumption)
                new_edge.append(self._create_data_element('assumption.resultfunction', nondet_method))
                graph.append(new_edge)
            previous_node = target_node

        # Add transition to violation node if line representing error location is reached
        target_node = self._create_node(violation=True)
        graph.append(target_node)
        for error_line in error_lines:
            new_edge = self._create_edge(previous_node.get('id'), target_node.get('id'), startline=error_line)
            graph.append(new_edge)

        # Add transition to sink node if an additional nondet call is performed
        sink_node = self._create_node()
        sink_node.set('id', 'sink')
        graph.append(sink_node)
        for nondet_method in nondet_methods:
            assumption = '\\result == 0;'  # dummy assumption
            new_edge = self._create_edge(previous_node.get('id'), sink_node.get('id'), assumption)
            new_edge.append(self._create_data_element('assumption.resultfunction', nondet_method))
            graph.append(new_edge)

        return graph

    def _create_graph(self, producer, filename, test_vector, nondet_methods, machine_model, error_lines):
        graph = self._create_graph_head(producer, filename, machine_model)
        return self._create_automaton(graph, test_vector, nondet_methods, error_lines)

    def create_witness(self, producer, filename, test_vector, nondet_methods, machine_model, error_lines):
        self._reset_node_id()
        witness = self._create_witness_header(filename)
        nondet_method_names = [m['name'] for m in nondet_methods]
        graph = self._create_graph(producer, filename, test_vector, nondet_method_names, machine_model, error_lines)
        witness.append(graph)

        xml_string = ET.tostring(witness, 'utf-8')
        minidom_parsed_xml = minidom.parseString(xml_string)
        return minidom_parsed_xml.toprettyxml(indent=(4 * ' '))
