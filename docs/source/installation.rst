Installation
==============

Anaconda is required for installation of this software.


Steps
------

1. Clone this `repository <https://github.com/KaareH/DTU_E23_41934_Advanced-BIM>`_ to your local machine.
2. Open up command prompt/terminal in the repository, and run:

    .. code-block:: console
        
        $ cd some/path/to/DTU_E23_41934_Advanced-BIM
3. Create the required environment by:
    
    .. code-block:: console
        
        $ conda env update --file environment.yml --prune
4. Activate the environment by:

    .. code-block:: console

        $ conda activate BIMEnv

5. Install the package either by:
    * Develop mode:
    
        .. code-block:: console

            $ conda develop ./src
    
    | or alternatively

    * Add local build channel (Typically for windows):

        .. code-block:: console
        
            $ conda config --add channels file:///C:\Users\<username>\conda-bld

    * Build package and install in environment:

        .. code-block:: console
            
            $ conda build . & conda install --use-local pyconbim --force-reinstall

6. Verify installation with:

    .. code-block:: console
        
        $ pytest .



Build documentation
------------------------
1.
    .. code-block:: console
        
        $ cd some/path/to/DTU_E23_41934_Advanced-BIM
2.
    .. code-block:: console

        $ sphinx-build -M html docs/source/ docs/build/
