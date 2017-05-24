from xml.etree import ElementTree as ET
import xml.dom.minidom as minidom
import utils
import os


_node_id_counter = -1


def _create_witness_header(filename):
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


def _create_data_element(keyname, text):
    data_el = ET.Element('data')
    data_el.text = str(text)
    data_el.set('key', str(keyname))
    return data_el


def _next_node_id():
    global _node_id_counter
    _node_id_counter += 1
    return 'A' + str(_node_id_counter)


def _create_node(entry=False, violation=False):
    node = ET.Element('node')
    node.set('id', _next_node_id())
    if entry:
        node.append(_create_data_element('entry', 'true'))
    if violation:
        node.append(_create_data_element('violation', 'true'))
    return node


def _create_edge(source, target, assumption=None, startline=None, assumption_scope=None):
    edge = ET.Element('edge')
    edge.set('source', source)
    edge.set('target', target)
    if startline:
        edge.append(_create_data_element('startline', startline))
    if assumption:
        edge.append(_create_data_element('assumption', assumption))
    if assumption_scope:
        edge.append(_create_data_element('assumption.scope', assumption_scope))

    return edge


def _create_graph(producer, filename, test_vector, var_map, machine_model):
    graph = ET.Element('graph')
    graph.set('edgedefault', 'directed')

    # Create data elements that describe witness
    graph.append(_create_data_element('witness-type', 'violation_witness'))
    graph.append(_create_data_element('sourcecodelang', 'C'))
    graph.append(_create_data_element('producer', producer))
    graph.append(_create_data_element('specification', 'CHECK( init(main()), LTL(G ! call(__VERIFIER_error())) )'))
    #graph.append(_create_data_element('testfile', test_file))
    #timestamp = utils.get_time()
    #graph.append(_create_data_element('creationtime', timestamp))
    graph.append(_create_data_element('programfile', filename))
    filehash = utils.get_hash(filename)
    graph.append(_create_data_element('programhash', filehash))
    graph.append(_create_data_element('architecture', machine_model))

    # Create entry node
    previous_node = _create_node(entry=True)
    graph.append(previous_node)

    for num, instantiation in test_vector.items():
        target_node = _create_node()
        graph.append(target_node)
        var_name = instantiation['name']
        line = var_map[var_name]['line']
        scope = var_map[var_name]['scope']
        assumption = var_name + ' == ' + instantiation['value'] + ';'
        new_edge = _create_edge(previous_node.get('id'), target_node.get('id'), assumption, line, scope)
        graph.append(new_edge)
        previous_node = target_node

    target_node = _create_node(violation=True)
    graph.append(target_node)
    new_edge = _create_edge(previous_node.get('id'), target_node.get('id'))
    graph.append(new_edge)

    return graph


def create_witness(producer, filename, test_vector, nondet_var_map, machine_model):
    witness = _create_witness_header(filename)
    graph = _create_graph(producer, filename, test_vector, nondet_var_map, machine_model)
    witness.append(graph)

    xml_string = ET.tostring(witness, 'utf-8')
    minidom_parsed_xml = minidom.parseString(xml_string)
    return minidom_parsed_xml.toprettyxml(indent=(4 * ' '))
