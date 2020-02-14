from setuptools import setup

requirements = [
    'skidl',
    'sympy',
    'lcapy'
]

setup(
    name='bem',
    version='0.1',
    description='BEM Driven Circuit Development',
    url='http://github.com/fefa4ka/schema-bem',
    author='Alexander Kondratev',
    author_email='alex@nder.work',
    license='MIT',
    packages=['bem'],
    install_requires=requirements,
    zip_safe=False
)
