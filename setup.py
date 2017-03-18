import os
import glob

from setuptools import setup, find_packages

media_data = [dirname[0] for dirname in os.walk('./media')]

program_name = 'pince'

setup(
    name=program_name,

    version='0.1.0',

    description='A reverse engineering tool that\'ll (hopefully) supply the place of Cheat Engine for linux',
    long_description='',

    url='https://github.com/korcankaraokcu/PINCE',

    author='Korcan KARAOKÇU',
    author_email='korcankaraokcu@gmail.com',

    maintainer='Çağrı ULAŞ',
    maintainer_email='cagriulas@gmail.com',

    license='GPLv3+',

    classifiers=[
        'Development Status :: 2 - Pre-Alpha',

        'Natural Language :: English',

        'Operating System :: POSIX :: Linux',

        'Intended Audience :: Developers',
        'Intended Audience :: Other Audience',
        'Topic :: Software Development :: Bug Tracking',
        'Topic :: Software Development :: Debuggers',
        'Topic :: Software Development :: Disassemblers',

        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',

        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],

    keywords='pince dissassembler tracer reverse-engineering gdb debugger',

    packages=find_packages(),

    install_requires=['pexpect', 'psutil', 'pyqt5', 'distorm3'],

    data_files=[("share/" + program_name + media_data[i].replace('.', ''),
                [icons for icons in glob.glob(media_data[i] + '/*')]) for i in range(1, 4)],

    scripts=['bin/pince-gui'],
)
