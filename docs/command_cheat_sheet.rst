Command Cheat Sheet
===================

edi
+++

Enable bash completion during development and add the edi bin folder to the PATH:

::

  source local_setup

Run the tests (including coverage):

::

  py.test-3 --cov=edi --cov-report=html

Debian
++++++

Build an edi .deb package directly:

::

  debuild -us -uc

Build an edi .deb package using git-buildpackage:

::
 
  gbp buildpackage

Install the resulting package:

::

  sudo dpkg -i ../edi_X.X.X_all.deb

Python
++++++

Create a source distribution of edi:

::

  python3 setup.py sdist

Install edi in editable mode (development setup):

::

  pip3 install -e .

Documentation
+++++++++++++

Build the shinx html documentation of edi:

::

  cd docs && make html

git
+++

Initial personalization of git:

::

  git config --global user.email "lueschem@gmail.com"
  git config --global user.name "Matthias Luescher"



