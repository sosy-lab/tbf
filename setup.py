#!/usr/bin/env python3

from setuptools import setup
import re
import os

with open('tbf/__init__.py') as inp:
    version = re.search('^__VERSION__\s*=\s*[\"\'](.*)[\"\']', inp.read(),
                        re.M).group(1)


def get_files(directory, parent):
    files = list()
    for path, directories, filenames in os.walk(directory):
        rel_path = os.path.relpath(path, parent)
        for filename in filenames:
            files.append(os.path.join(rel_path, filename))
    return files


# Collect package_data for testing tools
tools = ['afl', 'cpatiger', 'crest', 'fshell', 'klee', 'random']
tool_data = list()
for tool in tools:
    tool_dir = os.path.join('tbf/tools', tool)
    tool_data += get_files(tool_dir, 'tbf/tools')

validator_data = get_files('tbf/validators', 'tbf')

setup(
    name='tbf-test',
    version=version,
    author='Dirk Beyer',
    description='tbf, an Automatic Test-Case Generation and Execution Framework',
    url='https://github.com/sosy-lab/tbf',
    packages=['tbf', 'tbf.tools'],
    package_data={
        'tbf.tools': tool_data,
        'tbf': validator_data
    },
    entry_points={"console_scripts": ['tbf = tbf:main']},
    install_requires=[
        'pycparser>=2.18',
    ],
    setup_requires=[
        'nose>=1.0',
    ],
    tests_require=[
        'pylint',
        'nose>=1.0',
    ],
    test_suite = 'nose.collector',
    license='multiple',
    keywords='test execution test-case generation verification',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'Operation System :: POSIX :: Linux',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Software Development :: Testing',
    ],
    platforms=['Linux'],
)
