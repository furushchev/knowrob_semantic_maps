knowrob_semantic_maps
=====

Script to convert URDF to SemanticEnvironmentMap

``` bash
rosrun knowrob_semantic_maps urdf_to_sem

usage: urdf_to_sem [-h] [-n NAMESPACE] [-f] urdf [sem]

positional arguments:
  urdf                  Path to URDF file
  sem                   Path to output SemanticEnvironmentMap file
    
optional arguments:
  -h, --help            show this help message and exit
  -n NAMESPACE, --namespace NAMESPACE
                        Namespace of output map
  -f, --overwrite       Overwrite output file if exists
```

