from setuptools import setup, find_packages

from distutils.command.build_py import build_py

class NPMInstall(build_py):
  """Custom build command."""

  def run(self):
    self.run_command('npn install -g canvas canvas2svg kicad-utils netlistsvg"')
    build_py.run(self)

requirements = [
    'skidl',
    'peewee',
    'codenamize'
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
    package_dir={"bem": "bem"},
    include_package_data=True,
    package_data={"bem": ["*.js", "*.json"]},
    install_requires=requirements,
    zip_safe=False,
    test_suite="tests",
    cmdclass={
        'npm_install': NPMInstall
    }
)
