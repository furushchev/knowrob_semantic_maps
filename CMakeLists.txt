cmake_minimum_required(VERSION 2.8.3)
project(knowrob_semantic_maps)

find_package(catkin REQUIRED)
catkin_python_setup()

catkin_package(
  CATKIN_DEPENDS rospy
)

install(PROGRAMS
  scripts/URDF2SEM
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION})
install(DIRECTORY src
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION})

# catkin_add_nosetests(test)
