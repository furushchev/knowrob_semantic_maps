#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Yuki Furuta <furushchev@jsk.imi.i.u-tokyo.ac.jp>


import os
from urdf_to_sem import URDF2SEM


class FileNotFoundException(Exception):
    pass

def urdf_to_sem(urdf_path, sem_path=None, overwrite=False):
    if not os.path.exists(urdf_path):
        raise FileNotFoundException(urdf_path)
    if sem_path is None:
        base_name, _ = os.path.splitext(urdf_path)
        sem_path = base_name + ".owl"

    u2s = URDF2SEM(urdf_path, sem_path)
    print u2s.to_string()

    return True

