# Copyright (C) 2018 Henrique Pereira Coutada Miranda
# All rights reserved.
#
# This file is part of yambopy
#
"""
This file contains classes and methods to generate input files
"""

from qepy.pw import PwIn
from qepy.ph import PhIn
from qepy.matdyn import Matdyn
from yambopy.flow import PwTask, PhTask, P2yTask, YamboTask, DynmatTask, YambopyFlow

__all__ = [
"FiniteDifferencesPhonon",
"PwNscfTask",
"PhPhononTask"
]

class FiniteDifferencesPhononFlow():
    """
    This class takes as an input one structure and a phonon calculation.
    It produces a flow with the QE input files displaced along the phonon modes
    """
    def __init__(self,structure,phonon_modes,yambo_input,yambo_runlevel):
        self.structure = structure
        if not isinstance(phonon_modes,Matdyn):
            raise ValueError('phonon_modes must be an instance of Matdyn')
        self.phonon_modes = phonon_modes
        self.yambo_input = yambo_input
        self.yambo_runlevel = yambo_runlevel

    def get_tasks(self,path,kpoints,ecut,nscf_bands,nscf_kpoints=None,
                  modes_list=None,displacement=0.01,iqpoint=0):
        """
        Create a flow with all the tasks to perform the calculation
        """
        if modes_list is None: modes_list = list(range(self.phonon_modes.nmodes))

        tasks = []

        #create qe input from structure
        pwin = PwIn.from_structure_dict(self.structure,kpoints=kpoints,ecut=ecut)

        #apply the displacement in the structure
        for imode in modes_list:
            #displace structure
            input_mock = pwin.displace(self.phonon_modes.modes[iqpoint,imode],
                                       displacement=displacement)
            displaced_structure = input_mock.get_structure()

            #create scf, nscf and p2y task
            tmp_tasks = PwNscfTask(displaced_structure,kpoints,ecut,nscf_bands)
            qe_scf_task,qe_nscf_task,p2y_task = tmp_tasks
            tasks.extend(tmp_tasks)

            #add yambo_task
            yambo_task = YamboTask.from_runlevel(p2y_task,self.yambo_runlevel,self.yambo_input,
                                                 dependencies=p2y_task)
            tasks.append(yambo_task)

        return tasks

 
    def get_flow(self,path,kpoints,ecut,nscf_bands,nscf_kpoints=None,modes_list=None):

        tasks = self.get_tasks(path=path,kpoints=kpoints,ecut=ecut,nscf_bands=nscf_bands,
                               nscf_kpoints=nscf_kpoints,modes_list=modes_list)
       
        #put all the tasks in a flow
        yambo_flow = YambopyFlow.from_tasks(path,tasks)
        return yambo_flow


def PhPhononTask(structure,kpoints,ecut,qpoints=None):
    """
    Return a ScfTask and a series of phonon tasks
    """

    #create a QE scf task and run
    qe_input = PwIn.from_structure_dict(structure,kpoints=kpoints,ecut=ecut)
    qe_scf_task = PwTask.from_input(qe_input)

    #create phonon tasks
    if qpoints is None: qpoints = qe_input.kpoints
    ph_input = PhIn.from_qpoints(qpoints)
    ph_task = PhTask.from_scf_task([ph_input,qe_scf_task],dependencies=qe_scf_task)

    #create matdyn task
    matdyn_task = DynmatTask.from_phonon_task(ph_task,dependencies=ph_task)
 
    return qe_scf_task, ph_task, matdyn_task

def PwNscfTask(structure,kpoints,ecut,nscf_bands,nscf_kpoints=None):
    """
    Return a ScfTask, NscfTask and P2yTask preparing for a Yambo calculation
    """

    #create a QE scf task and run
    qe_input = PwIn.from_structure_dict(structure,kpoints=kpoints,ecut=ecut)
    qe_scf_task = PwTask.from_input(qe_input)

    #create a QE nscf task and run
    qe_input = qe_input.copy().set_nscf(nscf_bands)
    if nscf_kpoints is not None: qe_input.set_kpoints(nscf_kpoints) 
    qe_nscf_task = PwTask.from_input([qe_input,qe_scf_task],dependencies=qe_scf_task)

    #create a p2y nscf task and run
    p2y_task = P2yTask.from_nscf_task(qe_nscf_task)

    return qe_scf_task, qe_nscf_task, p2y_task