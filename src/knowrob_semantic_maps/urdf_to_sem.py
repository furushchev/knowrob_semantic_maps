#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Yuki Furuta <furushchev@jsk.imi.i.u-tokyo.ac.jp>

import os
from StringIO import StringIO
from urdf_parser_py.urdf import URDF
import tf.transformations as T
import numpy as np

from utils import UniqueStringGenerator
from gazebo import resolve_model_path


class URDF2SEM(object):
    def __init__(self, urdf_path, sem_path):
        self.nsmap = {
            "xsd": "http://www.w3.org/2001/XMLSchema#",
            "owl": "http://www.w3.org/2002/07/owl#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
            "srdl2": "http://knowrob.org/kb/srdl2.owl#",
            "owl2xml": "http://www.w3.org/2006/12/owl2-xml#",
            "knowrob": "http://knowrob.org/kb/knowrob.owl#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "srdl2-comp": "http://knowrob.org/kb/srdl2-comp.owl#",
            "srdl2-cap": "http://knowrob.org/kb/srdl2-cap.owl#",
            "qudt-unit": "http://qudt.org/vocab/unit#",
        }
        self.imports = [
            "package://knowrob_srdl/owl/srdl2-comp.owl",
            "package://knowrob_common/owl/knowrob.owl",
        ]
        self.id_gen = UniqueStringGenerator()
        self.urdf = URDF.from_xml_file(urdf_path)
        self.urdf.check_valid()

        basename = os.path.basename(sem_path)
        namespace, _ = os.path.splitext(basename)
        self.map_ns = namespace
        self.map_name = self.urdf.name + "_" + self.id_gen.gen()
        self.map_uri_base = "http://knowrob.org/kb/%s" % basename
        self.map_uri = self.map_uri_base + "#"
        self.nsmap[self.map_ns] = self.map_uri
        self.transformations = {}

    def to_string(self):
        s = StringIO()
        self.write_header(s)
        self.write_imports(s)
        self.write_instance(s)
        self.write_links(s)
        self.write_joints(s)
        self.write_footer(s)

        return s.getvalue()

    def write_header(self, s):
        s.write("""\
<?xml version="1.0"?>

<!-- =============================================== -->
<!-- | This file was autogenerated by URDF2SEM     | -->
<!-- =============================================== -->\n""")

        # write doctype
        s.write("""\n<!DOCTYPE rdf:RDF [\n""")
        for name, uri in self.nsmap.items():
            s.write("""<!ENTITY {name} "{uri}">\n""".format(**locals()))
        s.write("""]>\n\n""")

        # write rdf:RDF tag begin
        s.write("""<rdf:RDF xml:base="%s"\n""" % self.map_uri_base)
        s.write("""         xmlns="%s\"""" % self.map_uri)
        for name, uri in self.nsmap.items():
            s.write("""\n         xmlns:{name}="{uri}\"""".format(**locals()))
        s.write(""">\n""")

    def write_footer(self, s):
        s.write("""\n</rdf:RDF>\n""")

    def write_imports(self, s):
        s.write("""
    <!-- =========================================== -->
    <!-- |   Ontology Imports                      | -->
    <!-- =========================================== -->""")
        s.write("\n\n")
        s.write("""    <owl:Ontology rdf:about="{map_uri_base}">\n""".format(map_uri_base=self.map_uri_base))
        for imp in self.imports:
            s.write("""      <owl:imports rdf:resource="{imp}"/>\n""".format(imp=imp))
        s.write("""    </owl:Ontology>\n""")
        return s.getvalue()

    def write_instance(self, s):
        s.write("""
    <!-- =========================================== -->
    <!-- |   Semantic Environment Map Instance     | -->
    <!-- =========================================== -->

    <owl:NamedIndividual rdf:about="&{map_ns};{map_name}">
        <rdf:type rdf:resource="&knowrob;SemanticEnvironmentMap"/>
    </owl:NamedIndividual>

    <owl:NamedIndividual rdf:about="&{map_ns};timepoint_0000000001">
        <rdf:type rdf:resource="&knowrob;TimePoint"/>
    </owl:NamedIndividual>\n""".format(map_ns=self.map_ns, map_name=self.map_name))

    def write_link(self, s, link_name):
        map_ns = self.map_ns
        map_name = self.map_name
        prefix = self.map_name + "_"
        link = self.urdf.link_map[link_name]

        mesh_file_name = None
        mesh_scale = None
        if link.visual is not None:
            mesh_file_name = resolve_model_path(link.visual.geometry.filename)
            mesh_scale = "%f %f %f" % tuple(link.visual.geometry.scale)

        s.write("""
    <owl:NamedIndividual rdf:about="&{map_ns};{prefix}{link_name}">
        <rdf:type rdf:resource="&srdl2-comp;UrdfLink"/>
        <srdl2-comp:urdfName>{link_name}</srdl2-comp:urdfName>
        <knowrob:describedInMap rdf:resource="&{map_ns};{map_name}"/>""".format(**locals()))
        if link_name in self.urdf.child_map:
            for joint_name, _ in self.urdf.child_map[link_name]:
                s.write("""
        <srdl2-comp:succeedingJoint rdf:resource="&{map_ns};{prefix}{joint_name}"/>""".format(**locals()))
        if mesh_file_name is None:
            s.write("""
        <knowrob:hasVisual rdf:datatype="&xsd;boolean">false</knowrob:hasVisual>""")
        else:
            s.write("""
        <knowrob:pathToCadModel rdf:datatype="&xsd;string">{mesh_file_name}</knowrob:pathToCadModel>""".format(**locals()))
        if mesh_scale is not None:
            s.write("""
        <srdl2-comp:mesh_scale rdf:datatype="&xsd;string">{mesh_scale}</srdl2-comp:mesh_scale>""".format(**locals()))
        s.write("""
    </owl:NamedIndividual>\n""")

    def calc_transformation(self, name, relative_to=None):
        calc_from_joint = False
        if relative_to:
            if relative_to in self.urdf.link_map:
                parent_link_name = relative_to
            elif relative_to in self.urdf.joint_map:
                parent_link_name = self.urdf.joint_map[name].parent
                calc_from_joint = True
        else:
            parent_link_name = self.urdf.get_root()

        calc_to_joint = False
        if name in self.urdf.link_map:
            child_link_name = name
        elif name in self.urdf.joint_map:
            child_link_name = self.urdf.joint_map[name].child
            calc_to_joint = True

        chains = self.urdf.get_chain(parent_link_name, child_link_name,
                                     joints=True, links=True)
        if calc_from_joint:
            chains = chains[1:]
        if calc_to_joint:
            chains = chains[:-1]

        poses = []
        for name in chains:
            if name in self.urdf.joint_map:
                joint = self.urdf.joint_map[name]
                if joint.origin is not None:
                    poses.append(joint.origin)
            elif name in self.urdf.link_map:
                link = self.urdf.link_map[name]
                if link.visual is not None and link.visual.origin is not None:
                    poses.append(link.visual.origin)
        m = np.dot(T.translation_matrix((0,0,0)),
                   T.euler_matrix(0,0,0))
        for p in poses:
            n = np.dot(T.translation_matrix(tuple(p.xyz)),
                       T.euler_matrix(*tuple(p.rpy)))
            m = np.dot(m, n)
        t = T.translation_from_matrix(m)
        q = T.quaternion_from_matrix(m)
        return tuple(t), (q[3], q[0], q[1], q[2])

    def write_transformation(self, s, name, relative_to=None):
        if name in self.urdf.link_map and name not in self.urdf.parent_map:
            # no need to define transform if link has no parent link
            return

        prefix = self.map_name + "_"
        map_ns = self.map_ns
        perception_name = "SemanticMapPerception_" + self.id_gen.gen()
        transformation_name = "Transformation_" + self.id_gen.gen()

        t, q = self.calc_transformation(name, relative_to)
        translation = "%f %f %f" % t
        quaternion = "%f %f %f %f" % q

        # write perception
        s.write("""
    <owl:NamedIndividual rdf:about="&{map_ns};{perception_name}">
        <rdf:type rdf:resource="&knowrob;SemanticMapPerception"/>
        <knowrob:eventOccursAt rdf:resource="&{map_ns};{transformation_name}"/>
        <knowrob:startTime rdf:resource="&{map_ns};timepoint_0000000001"/>
        <knowrob:objectActedOn rdf:resource="&{map_ns};{prefix}{name}"/>
    </owl:NamedIndividual>""".format(**locals()))

        # write transformation
        s.write("""
    <owl:NamedIndividual rdf:about="&{map_ns};{transformation_name}">
        <rdf:type rdf:resource="&knowrob;Transformation"/>""".format(**locals()))
        if relative_to is not None and relative_to in self.transformations:
            parent_transformation_name = self.transformations[relative_to]
            s.write("""
        <knowrob:relativeTo rdf:resource="&{map_ns};{parent_transformation_name}"/>""".format(**locals()))
        s.write("""
        <knowrob:translation rdf:datatype="&xsd;string">{translation}</knowrob:translation>
        <knowrob:quaternion rdf:datatype="&xsd;string">{quaternion}</knowrob:quaternion>
    </owl:NamedIndividual>\n""".format(**locals()))
        self.transformations[name] = transformation_name

    def write_transformation_for_link(self, s, link_name, absolute=True):
        try:
            parent_joint_name = self.urdf.parent_map[link_name][0]
            joint = self.urdf.joint_map[parent_joint_name]
            parent_link_name = joint.parent
        except: return

        if absolute:
            self.write_transformation(s, link_name)
        else:
            self.write_transformation(s, link_name, relative_to=parent_link_name)

    def write_link_recursive(self, s, link_name, absolute=True):
        self.write_link(s, link_name)
        self.write_transformation_for_link(s, link_name, absolute)
        if link_name in self.urdf.child_map:
            for j, child_link in self.urdf.child_map[link_name]:
                self.write_link_recursive(s, child_link, absolute)

    def write_links(self, s, absolute=True):
        s.write("""

    <!-- =========================================== -->
    <!-- |   Robot Links                           | -->
    <!-- =========================================== -->""")
        s.write("\n\n")

        # link definition
        self.write_link_recursive(s, self.urdf.get_root(), absolute)

    def write_joint(self, s, joint_name):
        map_ns = self.map_ns
        map_name = self.map_name
        prefix = self.map_name + "_"
        joint = self.urdf.joint_map[joint_name]
        joint_type = "%sUrdfJoint" % joint.type.title()
        child_link_name = joint.child

        s.write("""
    <owl:NamedIndividual rdf:about="&{map_ns};{prefix}{joint_name}">
        <rdf:type rdf:resource="&srdl2-comp;{joint_type}"/>
        <srdl2-comp:urdfName>{joint_name}</srdl2-comp:urdfName>
        <knowrob:describedInMap rdf:resource="&{map_ns};{map_name}"/>
        <srdl2-comp:succeedingLink rdf:resource="&{map_ns};{prefix}{child_link_name}"/>
    </owl:NamedIndividual>""".format(**locals()))

    def write_transformation_for_joint(self, s, joint_name, absolute=True):
        if absolute:
            self.write_transformation(s, joint_name)
        else:
            parent_link_name = self.urdf.joint_map[joint_name].parent
            self.write_transformation(s, joint_name, relative_to=parent_link_name)

    def write_joint_recursive(self, s, parent_link_name, absolute=True):
        joints = []
        child_links = []
        if parent_link_name not in self.urdf.child_map:
            return
        for j, l in self.urdf.child_map[parent_link_name]:
            joints.append(j)
            child_links.append(l)
        for joint_name in joints:
            self.write_joint(s, joint_name)
            self.write_transformation_for_joint(s, joint_name, absolute)
        for child_link_name in child_links:
            self.write_joint_recursive(child_link_name, absolute)

    def write_joints(self, s, absolute=True):
        if len(self.urdf.joints) == 0:
            return

        s.write("""

    <!-- =========================================== -->
    <!-- |   Robot Joints                          | -->
    <!-- =========================================== -->""")
        s.write("\n\n")

        # joint definition
        self.write_joint_recursive(s, self.urdf.get_root(), absolute)
