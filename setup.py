#!/usr/bin/env python

from distutils.core import setup

setup(
    name='odr-radiodns-bridge',
    version='1.0',
    packages=['odr', 'odr.radiodns'],
    package_dir = {'' : 'src'}
    url='https://github.com/nickpiggott/odr-radiodns-bridge',
    license='GNU Lesser General Public License 2.1',
    author='Nick Piggott',
    author_email='nick@piggott.eu',
    description='Tools to bridge RadioDNS applications into the OpenDigitalRadio environment'
)
