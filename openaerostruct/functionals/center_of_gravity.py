from __future__ import division, print_function
import numpy as np

from openmdao.api import ExplicitComponent

try:
    from openaerostruct.fortran import OAS_API
    fortran_flag = True
    data_type = float
except:
    fortran_flag = False
    data_type = complex


class CenterOfGravity(ExplicitComponent):
    """
    Compute the center of gravity of the entire aircraft based on the inputted W0
    and its corresponding cg and the weighted sum of each surface's structural
    weight and location.

    Note that we add information from each lifting surface.

    Parameters
    ----------
    structural_weight : float
        Total weight of the structural spar for a given surface.
    cg_location[3] : numpy array
        Location of the structural spar's cg for a given surface.

    total_weight : float
        Total weight of the entire aircraft, including W0, all structural weights,
        and fuel.
    fuelburn : float
        Computed fuel burn in kg based on the Breguet range equation.

    Returns
    -------
    cg[3] : numpy array
        The x, y, z coordinates of the center of gravity for the entire aircraft.

    """

    def initialize(self):
        self.metadata.declare('surfaces', type_=list, required=True)

    def setup(self):
        for surface in self.metadata['surfaces']:
            name = surface['name']
            self.add_input(name + 'structural_weight', val=1.)
            self.add_input(name + 'cg_location', val=np.random.rand(3))

        self.add_input('total_weight', val=1.)
        self.add_input('fuelburn', val=1.)
        self.add_input('W0', val=1.)
        self.add_input('load_factor', val=1.)

        self.add_output('cg', val=np.random.rand(3))

    def compute(self, inputs, outputs):

        g = 9.80665 * inputs['load_factor']
        W0 = inputs['W0']
        cg = inputs['empty_cg']
        W0_cg = W0 * cg * g

        spar_cg = np.zeros(3)

        # Loop through the surfaces and compute the weighted cg location
        # of all structural spars
        for surface in self.metadata['surfaces']:
            name = surface['name']
            spar_cg += inputs[name + 'cg_location'] * inputs[name + 'structural_weight']

        # Compute the total cg of the aircraft based on the empty weight cg and
        # the structures cg. Here we assume the fuel weight is at the cg.
        outputs['cg'] = (W0_cg + spar_cg) / (inputs['total_weight'] - inputs['fuelburn'] * g)

        arange = np.arange(3)

        for surface in self.metadata['surfaces']:
            name = surface['name']
            self.declare_partials('cg', name + 'cg_location', rows=arange, cols=arange)

    def compute_partials(self, inputs, outputs, partials):

        g = 9.80665 * inputs['load_factor']
        W0 = inputs['W0']
        cg = inputs['empty_cg']
        W0_cg = W0 * cg * g

        spar_cg = np.zeros(3)

        # Loop through the surfaces and compute the weighted cg location
        # of all structural spars
        for surface in self.metadata['surfaces']:
            name = surface['name']
            spar_cg += inputs[name + 'cg_location'] * inputs[name + 'structural_weight']

        partials['cg', 'total_weight'] = \
            -(W0_cg + spar_cg) / (inputs['total_weight'] - inputs['fuelburn'] * g) ** 2
        partials['cg', 'fuelburn'] = \
            g * (W0_cg + spar_cg) / (inputs['total_weight'] - inputs['fuelburn'] * g) ** 2

        for surface in self.metadata['surfaces']:
            name = surface['name']
            partials['cg', name + 'cg_location'] = inputs[name + 'structural_weight'] \
                / (inputs['total_weight'] - inputs['fuelburn'] * g)
            partials['cg', name + 'structural_weight'] = inputs[name + 'cg_location'] \
                / (inputs['total_weight'] - inputs['fuelburn'] * g)