Installation
==============

Anaconda is required for installation of this software.

Steps
------

1. Clone this `repository <https://github.com/KaareH/DTU_E23_41934_Advanced-BIM>`_ to your local machine.
2. Open up command prompt/terminal in the repository, and :code:`cd Assingments/A3`.
3. Create the required environment by :code:`conda env update --file .\environment.yml --prune`.
4. Activate the environment by :code:`conda activate BIMEnv`.
5. Install the package either by:
    * :code:`conda develop ./src`.
    
    | or alternatively

    * Add local build channel :code:`conda config --add channels file:///C:\Users\<username>\conda-bld` (Typically for windows).
    * Build package and add to environment :code:`conda build . & conda install --use-local pyconbim --force-reinstall`.

6. Verify installation wiht :code:`pytest .`.


Build documentation
------------------------
1. :code:`cd Assingments/A3`.
2. :code:`sphinx-build -M html docs/source/ docs/build/`.
