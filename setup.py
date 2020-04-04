from setuptools import setup, find_packages

from distutils.command.build import build

class NPMInstall(build):
    def run(self):
        self.run_command("npm install -g canvas canvas2svg kicad-utils netlistsvg")
        build.run(self)

requirements = [
    'skidl',
    'peewee'
]

setup(
    name='bem',
    version='0.1',
    description='BEM Driven Circuit Development',
    url='http://github.com/fefa4ka/schema-bem',
    author='Alexander Kondratev',
    author_email='alex@nder.work',
    license='MIT',
    packages=find_packages(exclude=["tests"]),
    install_requires=requirements,
    zip_safe=False,
    cmdclass={
        'npm_install': NPMInstall
    },
)
