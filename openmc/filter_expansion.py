from numbers import Integral, Real

import lxml.etree as ET

import openmc.checkvalue as cv
from . import Filter


class ExpansionFilter(Filter):
    """Abstract filter class for functional expansions."""

    def __init__(self, order, filter_id=None):
        self.order = order
        self.id = filter_id

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        else:
            return hash(self) == hash(other)

    @property
    def order(self):
        return self._order

    @order.setter
    def order(self, order):
        cv.check_type('expansion order', order, Integral)
        cv.check_greater_than('expansion order', order, 0, equality=True)
        self._order = order

    def to_xml_element(self):
        """Return XML Element representing the filter.

        Returns
        -------
        element : lxml.etree._Element
            XML element containing Legendre filter data

        """
        element = ET.Element('filter')
        element.set('id', str(self.id))
        element.set('type', self.short_name.lower())

        subelement = ET.SubElement(element, 'order')
        subelement.text = str(self.order)

        return element

    @classmethod
    def from_xml_element(cls, elem, **kwargs):
        filter_id = int(elem.get('id'))
        order = int(elem.find('order').text)
        return cls(order, filter_id=filter_id)

    def merge(self, other):
        """Merge this filter with another.

        This overrides the behavior of the parent Filter class, since its
        merging technique is to take the union of the set of bins of each
        filter. That technique does not apply to expansion filters, since the
        argument should be the maximum filter order rather than the list of all
        bins.

        Parameters
        ----------
        other : openmc.Filter
            Filter to merge with

        Returns
        -------
        merged_filter : openmc.Filter
            Filter resulting from the merge

        """

        if not self.can_merge(other):
            msg = f'Unable to merge "{type(self)}" with "{type(other)}"'
            raise ValueError(msg)

        # Create a new filter with these bins and a new auto-generated ID
        return type(self)(max(self.order, other.order))


class LegendreFilter(ExpansionFilter):
    r"""Score Legendre expansion moments up to specified order.

    This filter allows scores to be multiplied by Legendre polynomials of the
    change in particle angle (:math:`\mu`) up to a user-specified order.

    Parameters
    ----------
    order : int
        Maximum Legendre polynomial order
    filter_id : int or None
        Unique identifier for the filter

    Attributes
    ----------
    order : int
        Maximum Legendre polynomial order
    id : int
        Unique identifier for the filter
    num_bins : int
        The number of filter bins

    """

    def __hash__(self):
        string = type(self).__name__ + '\n'
        string += '{: <16}=\t{}\n'.format('\tOrder', self.order)
        return hash(string)

    def __repr__(self):
        string = type(self).__name__ + '\n'
        string += '{: <16}=\t{}\n'.format('\tOrder', self.order)
        string += '{: <16}=\t{}\n'.format('\tID', self.id)
        return string

    @ExpansionFilter.order.setter
    def order(self, order):
        ExpansionFilter.order.__set__(self, order)
        self.bins = [f'P{i}' for i in range(order + 1)]

    @classmethod
    def from_hdf5(cls, group, **kwargs):
        if group['type'][()].decode() != cls.short_name.lower():
            raise ValueError("Expected HDF5 data for filter type '"
                             + cls.short_name.lower() + "' but got '"
                             + group['type'][()].decode() + " instead")

        filter_id = int(group.name.split('/')[-1].lstrip('filter '))

        out = cls(group['order'][()], filter_id)

        return out


class SpatialLegendreFilter(ExpansionFilter):
    r"""Score Legendre expansion moments in space up to specified order.

    This filter allows scores to be multiplied by Legendre polynomials of the
    the particle's position along a particular axis, normalized to a given
    range, up to a user-specified order.

    Parameters
    ----------
    order : int
        Maximum Legendre polynomial order
    axis : {'x', 'y', 'z'}
        Axis along which to take the expansion
    minimum : float
        Minimum value along selected axis
    maximum : float
        Maximum value along selected axis
    filter_id : int or None
        Unique identifier for the filter

    Attributes
    ----------
    order : int
        Maximum Legendre polynomial order
    axis : {'x', 'y', 'z'}
        Axis along which to take the expansion
    minimum : float
        Minimum value along selected axis
    maximum : float
        Maximum value along selected axis
    id : int
        Unique identifier for the filter
    num_bins : int
        The number of filter bins

    """

    def __init__(self, order, axis, minimum, maximum, filter_id=None):
        super().__init__(order, filter_id)
        self.axis = axis
        self.minimum = minimum
        self.maximum = maximum

    def __hash__(self):
        string = type(self).__name__ + '\n'
        string += '{: <16}=\t{}\n'.format('\tOrder', self.order)
        string += '{: <16}=\t{}\n'.format('\tAxis', self.axis)
        string += '{: <16}=\t{}\n'.format('\tMin', self.minimum)
        string += '{: <16}=\t{}\n'.format('\tMax', self.maximum)
        return hash(string)

    def __repr__(self):
        string = type(self).__name__ + '\n'
        string += '{: <16}=\t{}\n'.format('\tOrder', self.order)
        string += '{: <16}=\t{}\n'.format('\tAxis', self.axis)
        string += '{: <16}=\t{}\n'.format('\tMin', self.minimum)
        string += '{: <16}=\t{}\n'.format('\tMax', self.maximum)
        string += '{: <16}=\t{}\n'.format('\tID', self.id)
        return string

    @ExpansionFilter.order.setter
    def order(self, order):
        ExpansionFilter.order.__set__(self, order)
        self.bins = [f'P{i}' for i in range(order + 1)]

    @property
    def axis(self):
        return self._axis

    @axis.setter
    def axis(self, axis):
        cv.check_value('axis', axis, ('x', 'y', 'z'))
        self._axis = axis

    @property
    def minimum(self):
        return self._minimum

    @minimum.setter
    def minimum(self, minimum):
        cv.check_type('minimum', minimum, Real)
        self._minimum = minimum

    @property
    def maximum(self):
        return self._maximum

    @maximum.setter
    def maximum(self, maximum):
        cv.check_type('maximum', maximum, Real)
        self._maximum = maximum

    @classmethod
    def from_hdf5(cls, group, **kwargs):
        if group['type'][()].decode() != cls.short_name.lower():
            raise ValueError("Expected HDF5 data for filter type '"
                             + cls.short_name.lower() + "' but got '"
                             + group['type'][()].decode() + " instead")

        filter_id = int(group.name.split('/')[-1].lstrip('filter '))
        order = group['order'][()]
        axis = group['axis'][()].decode()
        min_, max_ = group['min'][()], group['max'][()]

        return cls(order, axis, min_, max_, filter_id)

    def to_xml_element(self):
        """Return XML Element representing the filter.

        Returns
        -------
        element : lxml.etree._Element
            XML element containing Legendre filter data

        """
        element = super().to_xml_element()
        subelement = ET.SubElement(element, 'axis')
        subelement.text = self.axis
        subelement = ET.SubElement(element, 'min')
        subelement.text = str(self.minimum)
        subelement = ET.SubElement(element, 'max')
        subelement.text = str(self.maximum)

        return element

    @classmethod
    def from_xml_element(cls, elem, **kwargs):
        filter_id = int(elem.get('id'))
        order = int(elem.find('order').text)
        axis = elem.find('axis').text
        minimum = float(elem.find('min').text)
        maximum = float(elem.find('max').text)
        return cls(order, axis, minimum, maximum, filter_id=filter_id)


class SphericalHarmonicsFilter(ExpansionFilter):
    r"""Score spherical harmonic expansion moments up to specified order.

    This filter allows you to obtain real spherical harmonic moments of either
    the particle's direction or the cosine of the scattering angle. Specifying
    a filter with order :math:`\ell` tallies moments for all orders from 0 to
    :math:`\ell`.

    Parameters
    ----------
    order : int
        Maximum spherical harmonics order, :math:`\ell`
    filter_id : int or None
        Unique identifier for the filter

    Attributes
    ----------
    order : int
        Maximum spherical harmonics order, :math:`\ell`
    id : int
        Unique identifier for the filter
    cosine : {'scatter', 'particle'}
        How to handle the cosine term.
    num_bins : int
        The number of filter bins

    """

    def __init__(self, order, filter_id=None):
        super().__init__(order, filter_id)
        self._cosine = 'particle'

    def __hash__(self):
        string = type(self).__name__ + '\n'
        string += '{: <16}=\t{}\n'.format('\tOrder', self.order)
        string += '{: <16}=\t{}\n'.format('\tCosine', self.cosine)
        return hash(string)

    def __repr__(self):
        string = type(self).__name__ + '\n'
        string += '{: <16}=\t{}\n'.format('\tOrder', self.order)
        string += '{: <16}=\t{}\n'.format('\tCosine', self.cosine)
        string += '{: <16}=\t{}\n'.format('\tID', self.id)
        return string

    @ExpansionFilter.order.setter
    def order(self, order):
        ExpansionFilter.order.__set__(self, order)
        self.bins = [f'Y{n},{m}'
                     for n in range(order + 1)
                     for m in range(-n, n + 1)]

    @property
    def cosine(self):
        return self._cosine

    @cosine.setter
    def cosine(self, cosine):
        cv.check_value('Spherical harmonics cosine treatment', cosine,
                       ('scatter', 'particle'))
        self._cosine = cosine

    @classmethod
    def from_hdf5(cls, group, **kwargs):
        if group['type'][()].decode() != cls.short_name.lower():
            raise ValueError("Expected HDF5 data for filter type '"
                             + cls.short_name.lower() + "' but got '"
                             + group['type'][()].decode() + " instead")

        filter_id = int(group.name.split('/')[-1].lstrip('filter '))

        out = cls(group['order'][()], filter_id)
        out.cosine = group['cosine'][()].decode()

        return out

    def to_xml_element(self):
        """Return XML Element representing the filter.

        Returns
        -------
        element : lxml.etree._Element
            XML element containing spherical harmonics filter data

        """
        element = super().to_xml_element()
        element.set('cosine', self.cosine)
        return element

    @classmethod
    def from_xml_element(cls, elem, **kwargs):
        filter_id = int(elem.get('id'))
        order = int(elem.find('order').text)
        filter = cls(order, filter_id=filter_id)
        filter.cosine = elem.get('cosine')
        return filter


class ZernikeFilter(ExpansionFilter):
    r"""Score Zernike expansion moments in space up to specified order.

    This filter allows scores to be multiplied by Zernike polynomials of the
    particle's position normalized to a given unit circle, up to a
    user-specified order. The standard Zernike polynomials follow the
    definition by Born and Wolf, *Principles of Optics* and are defined as

    .. math::
        Z_n^m(\rho, \theta) = R_n^m(\rho) \cos (m\theta), \quad m > 0

        Z_n^{m}(\rho, \theta) = R_n^{m}(\rho) \sin (m\theta), \quad m < 0

        Z_n^{m}(\rho, \theta) = R_n^{m}(\rho), \quad m = 0

    where the radial polynomials are

    .. math::
        R_n^m(\rho) = \sum\limits_{k=0}^{(n-m)/2} \frac{(-1)^k (n-k)!}{k! (
        \frac{n+m}{2} - k)! (\frac{n-m}{2} - k)!} \rho^{n-2k}.

    With this definition, the integral of :math:`(Z_n^m)^2` over the unit disk
    is :math:`\frac{\epsilon_m\pi}{2n+2}` for each polynomial where
    :math:`\epsilon_m` is 2 if :math:`m` equals 0 and 1 otherwise.

    Specifying a filter with order N tallies moments for all :math:`n` from 0
    to N and each value of :math:`m`. The ordering of the Zernike polynomial
    moments follows the ANSI Z80.28 standard, where the one-dimensional index
    :math:`j` corresponds to the :math:`n` and :math:`m` by

    .. math::
        j = \frac{n(n + 2) + m}{2}.

    ----- This is the start of my stuff -----
    This filter also allows scores to be calculated over a regular polygon
    with the number of sides on the polygon equal to num_sides. If num_sides
    is the default of 0, the filter will score over the unit disk. However,
    if num_sides is >= 3, the filter will score over the corresponding regular
    polygon.

    The transformation over the regular polygon follows the same math as the
    score calculation of the circular Zernike polynomials except for the
    radius normalization. The Zernike polynomials are orthonormal over the
    values of rho [0, 1]. Given a disk with an outer radius R != 1, the local
    radius r at a point x,y is transformed into rho by dividing by r.

    .. math::
        rho = \frac{r}{R}.

    A similar normalization occurs for the polygon tally, however, R is now
    a function of theta. R, the variable radius at each theta, is the
    distance from the center of the polygon to the edge of the polygon.
    R follows the definition by Ferreira, Lopez, Navarro, and Sinusia,
    *Orthogonal systems of Zernike type in polygons and polygonal facets*.
    
    R(:math:'\theta') is defined as

    ..math::
        R(\theta) = \frac{R_0 \cos (\alpha)}
        {\cos (U_alpha(\theta)}

    Where :math:'R_0' is the radius of the polygon, :math:'alpha' is half the
    spanned by a single sector of the polygon, and :math:'U_{\alpha}' is an
    intermediate function used to track the angle trough the current sector.

    :math:'\alpha' is given as

    ..math::
        \alpha = \frac{\pi}{p}

    where :math:'p' is the number of sides of the polgon.

    :math:'U_{\alpha}' is given as

    ..math::
        U_{\alpha}(\theta) = \theta - int( \frac{\theta + \alpha}{2 \alpha})
        2 \alpha

    ----- End of my stuff -----
    

    Parameters
    ----------
    order : int
        Maximum Zernike polynomial order
    x : float
        x-coordinate of center of circle for normalization
    y : float
        y-coordinate of center of circle for normalization
    r : float
        Radius of circle for normalization
    num_sides : int, optional
        Number of sides of the regular polygon for normalization

    Attributes
    ----------
    order : int
        Maximum Zernike polynomial order
    x : float
        x-coordinate of center of circle for normalization
    y : float
        y-coordinate of center of circle for normalization
    r : float
        Radius of circle for normalization
    num_sides : int, optional
        Number of sides of the regular polygon for normalization
    id : int
        Unique identifier for the filter
    num_bins : int
        The number of filter bins

    """

    def __init__(self, order, x=0.0, y=0.0, r=1.0, num_sides=0, filter_id=None):
        super().__init__(order, filter_id)
        self.x = x
        self.y = y
        self.r = r
        self.num_sides = int(num_sides)

    def __hash__(self):
        string = type(self).__name__ + '\n'
        string += '{: <16}=\t{}\n'.format('\tOrder', self.order)
        string += '{: <16}=\t{}\n'.format('\tX', self.x)
        string += '{: <16}=\t{}\n'.format('\tY', self.y)
        string += '{: <16}=\t{}\n'.format('\tR', self.r)
        string += '{: <16}=\t{}\n'.format('\tNumSides', self.num_sides)
        return hash(string)

    def __repr__(self):
        string = type(self).__name__ + '\n'
        string += '{: <16}=\t{}\n'.format('\tOrder', self.order)
        string += '{: <16}=\t{}\n'.format('\tNumSides', self.num_sides)
        string += '{: <16}=\t{}\n'.format('\tID', self.id)
        return string

    @ExpansionFilter.order.setter
    def order(self, order):
        ExpansionFilter.order.__set__(self, order)
        self.bins = [f'Z{n},{m}'
                     for n in range(order + 1)
                     for m in range(-n, n + 1, 2)]

    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, x):
        cv.check_type('x', x, Real)
        self._x = x

    @property
    def y(self):
        return self._y

    @y.setter
    def y(self, y):
        cv.check_type('y', y, Real)
        self._y = y

    @property
    def r(self):
        return self._r

    @r.setter
    def r(self, r):
        cv.check_type('r', r, Real)
        self._r = r

    @property
    def num_sides(self):
        return self._num_sides

    @num_sides.setter
    def num_sides(self, num_sides):
        cv.check_type('num_sides', num_sides, int)

        if (num_sides == 0):
            self._num_sides = 0
            return

        if (num_sides < 3):
            raise ValueError("The number of sides, {}, is not the "
                             + "default of 0, corresponding to a "
                             + "disk, and is less than 3, the fewest "
                             + "number of sides a regular polygon can "
                             + "have".format(num_sides))
        self._num_sides = num_sides

    @classmethod
    def from_hdf5(cls, group, **kwargs):
        if group['type'][()].decode() != cls.short_name.lower():
            raise ValueError("Expected HDF5 data for filter type '"
                             + cls.short_name.lower() + "' but got '"
                             + group['type'][()].decode() + " instead")

        filter_id = int(group.name.split('/')[-1].lstrip('filter '))
        order = group['order'][()]
        x, y, r =  group['x'][()], group['y'][()], group['r'][()]
        num_sides = group['num_sides'][()]

        return cls(order, x, y, r, num_sides, filter_id)

    def to_xml_element(self):
        """Return XML Element representing the filter.

        Returns
        -------
        element : lxml.etree._Element
            XML element containing Zernike filter data

        """
        element = super().to_xml_element()
        subelement = ET.SubElement(element, 'x')
        subelement.text = str(self.x)
        subelement = ET.SubElement(element, 'y')
        subelement.text = str(self.y)
        subelement = ET.SubElement(element, 'r')
        subelement.text = str(self.r)
        subelement = ET.SubElement(element, 'num_sides')
        subelement.text = str(self.num_sides)

        return element

    @classmethod
    def from_xml_element(cls, elem, **kwargs):
        filter_id = int(elem.get('id'))
        order = int(elem.find('order').text)
        x = float(elem.find('x').text)
        y = float(elem.find('y').text)
        r = float(elem.find('r').text)
        num_sides = int(elem.find('num_sides').text)
        return cls(order, x, y, r, num_sides, filter_id=filter_id)


class ZernikeRadialFilter(ZernikeFilter):
    r"""Score the :math:`m = 0` (radial variation only) Zernike moments up to
    specified order.

    The Zernike polynomials are defined the same as in :class:`ZernikeFilter`.

    .. math::

        Z_n^{0}(\rho, \theta) = R_n^{0}(\rho)

    where the radial polynomials are

    .. math::
        R_n^{0}(\rho) = \sum\limits_{k=0}^{n/2} \frac{(-1)^k (n-k)!}{k! ((
        \frac{n}{2} - k)!)^{2}} \rho^{n-2k}.

    With this definition, the integral of :math:`(Z_n^0)^2` over the unit disk
    is :math:`\frac{\pi}{n+1}`.

    If there is only radial dependency, the polynomials are integrated over
    the azimuthal angles. The only terms left are :math:`Z_n^{0}(\rho, \theta)
    = R_n^{0}(\rho)`. Note that :math:`n` could only be even orders.
    Therefore, for a radial Zernike polynomials up to order of :math:`n`,
    there are :math:`\frac{n}{2} + 1` terms in total. The indexing is from the
    lowest even order (0) to highest even order.

    Parameters
    ----------
    order : int
        Maximum radial Zernike polynomial order
    x : float
        x-coordinate of center of circle for normalization
    y : float
        y-coordinate of center of circle for normalization
    r : float
        Radius of circle for normalization

    Attributes
    ----------
    order : int
        Maximum radial Zernike polynomial order
    x : float
        x-coordinate of center of circle for normalization
    y : float
        y-coordinate of center of circle for normalization
    r : float
        Radius of circle for normalization
    id : int
        Unique identifier for the filter
    num_bins : int
        The number of filter bins

    """

    @ExpansionFilter.order.setter
    def order(self, order):
        ExpansionFilter.order.__set__(self, order)
        self.bins = [f'Z{n},0' for n in range(0, order+1, 2)]
