#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Yuki Furuta <furushchev@jsk.imi.i.u-tokyo.ac.jp>

import copy
import lxml.etree as E


class NoLinkFoundException(Exception):
    pass
class NoJointFoundException(Exception):
    pass
class InvalidJointException(Exception):
    pass
class InvalidLinkException(Exception):
    pass

class URDFParser(object):
    def __init__(self, path):
        self.tree = E.parse(path)
        self.name = None
        self.links = []
        self.joints = []
        self.root_link = None
        self.link_joint_tree = {}

    def parse(self):
        self.name = self.tree.getroot().get("name")
        self.links = [e.get("name") for e in self.tree.xpath("//robot/link")]
        if len(self.links) == 0:
            raise NoLinkFoundException
        elif len(self.links) == 1:
            self.root_link = self.links[0]
            return
        else:
            root_link_candidates = copy.deepcopy(self.links)
            joints = self.tree.xpath("//robot/joint")
            if len(joints) == 0:
                raise NoJointFoundException("%d > 1 link are found, but no joint found." % len(self.links))
            else:
                self.joints = [e.get("name") for e in joints]
                for j in joints:
                    joint_name = j.get("name")

                    if j.find("parent") is None:
                        raise InvalidJointException("no parent link in joint " + joint_name)
                    if j.find("child") is None:
                        raise InvalidJointException("no child link in joint " + joint_name)

                    parent_link = j.find("parent").get("link")
                    child_link = j.find("child").get("link")

                    if parent_link in self.link_joint_tree.keys():
                        if joint_name not in self.link_joint_tree[parent_link]:
                            self.link_joint_tree[parent_link].append(joint_name)
                    else:
                        self.link_joint_tree[parent_link] = [joint_name]
                    root_link_candidates.remove(child_link)
                if len(root_link_candidates) > 1:
                    raise InvalidLinkException("There is more than one root link: %s" % str(root_link_candidates))
                self.root_link = root_link_candidates[0]
        if self.root_link is None:
            raise InvalidLinkException("No root link found")
    def get_child_joints(self, link_name):
        if link_name in self.link_joint_tree.keys():
            return self.link_joint_tree[link_name]
        else:
            return list()


if __name__ == '__main__':
    from rospkg import RosPack
    import os
    pkg = RosPack().get_path("eusurdf")
    p = URDFParser(os.path.join(pkg, "models", "hitachi-fiesta-refrigerator", "model.urdf"))
    p.parse()
    print p.name
    print p.root_link
