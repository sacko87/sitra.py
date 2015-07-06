from setuptools import setup

setup(name='sitra',
      version='0.1',
      description='A Python implementation of the Simple Transformer (SiTra).',
      url='https://github.com/sacko87/sitra.py',
      author='John T. Saxon',
      author_email='j.t.saxon@cs.bham.ac.uk',
      packages=['sitra'],
      package_dir={'sitra': 'src'},
      install_requires=[
        'six',
        'wrapt'
      ])
    
