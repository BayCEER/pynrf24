#!/usr/bin/env python

try:
    from setuptools import setup
except ImportError as ierr:
    print 'Import error :' + str(ierr)
    from distutils.core import setup

setup(
    name='nrf24',
    version='1.0.5',
    packages=['nrf24'],
    description='Python port of the RF24 library for NRF24L01+ radios',
    author='Stefan Lau (modified by Stefan Holzheu)',
    author_email='stefan.holzheu@buni-bayreuth.de',
    license='GPL2',
    keywords='nrf24 radio',
    classifiers=['Programming Language :: Python'],
)
