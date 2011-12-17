from zope.interface import implements

from plone.batching.interfaces import IBatch
from plone.batching.utils import (
    opt, calculate_leapback, calculate_leapforward,
    calculate_pagenumber, calculate_pagerange, calculate_quantum_leap_gap)


class BaseBatch(object):
    """Create a sequence batch"""

    implements(IBatch)

    size = first = start = end = 0
    navlist = []
    numpages = pagenumber = pagerange = pagenumber = 0
    orphan = overlap = 0
    b_start_str = 'b_start'

    def __init__(self, sequence, size, start=0, end=0, orphan=0, overlap=0, pagerange=7):
        """ Encapsulate sequence in batches of size
        sequence    - the data to batch.
        size        - the number of items in each batch.
        start       - the first element of sequence to include in batch (0-index)
        end         - the last element of sequence to include in batch (0-index, optional)
        orphan      - the next page will be combined with the current page if it does not contain more than orphan elements
        overlap     - the number of overlapping elements in each batch
        pagerange   - the number of pages to display in the navigation
        """
        start += 1
        self._sequence = sequence
        self._size = size
        self.orphan = orphan
        self.overlap = overlap
        self.pagerange = pagerange

        self.initialize(start, end, size)

    def initialize(self, start, end, size):
        start, end, sz = opt(start, end, size, self.orphan, self.sequence_length)

        self.pagesize = sz
        self.start = start
        self.end = end

        self.first = max(start - 1, 0)
        self.length = self.end - self.first

        self.last = self.sequence_length - size

        # Set up the total number of pages
        self.numpages = calculate_pagenumber(self.sequence_length - self.orphan, self.pagesize, self.overlap)

        # Set up the current page number
        self._pagenumber = calculate_pagenumber(self.start, self.pagesize, self.overlap)

    @property
    def navlist(self):
        start = max(self.pagenumber - (self.pagerange / 2), 1)
        end = min(start + self.pagerange - 1, self.lastpage)
        return range(start, end + 1)

    def getPagenumber(self):
        return self._pagenumber

    def setPagenumber(self, pagenumber):
        start = max(0, (pagenumber - 1) * self._size) + 1
        self.initialize(start, 0, self._size)
        self._pagenumber = pagenumber

    pagenumber = property(getPagenumber, setPagenumber)

    @classmethod
    def fromPagenumber(cls, items, pagesize=20, pagenumber=1, navlistsize=5):
        start = max(0, (pagenumber - 1) * pagesize)
        return cls(items, pagesize, start, pagerange=navlistsize)

    @property
    def sequence_length(self):
        return getattr(self._sequence, 'actual_result_count', len(self._sequence))

    def __len__(self):
        return self.sequence_length

    @property
    def next(self):
        if self.end >= (self.last + self.pagesize):
            return None
        return Batch(self._sequence, self._size, self.end - self.overlap,
            0, self.orphan, self.overlap)

    @property
    def previous(self):
        if not self.first:
            return None
        return Batch(self._sequence, self._size,
            self.first - self._size + self.overlap, 0, self.orphan, self.overlap)

    def __getitem__(self, index):
        actual = getattr(self._sequence, 'actual_result_count', None)
        if actual is not None and actual != len(self._sequence):
            # optmized batch that contains only the wanted items in the sequence
            return self._sequence[index]
        if index < 0:
            if index + self.end < self.first:
                raise IndexError(index)
            return self._sequence[index + self.end]
        if index >= self.length:
            raise IndexError(index)
        return self._sequence[index + self.first]

    # methods from plone.app.content
    @property
    def firstpage(self):
        return 1

    @property
    def lastpage(self):
        pages = self.sequence_length / self.pagesize
        if self.sequence_length % self.pagesize:
            pages += 1
        return pages

    @property
    def islastpage(self):
        return self.lastpage == self.pagenumber

    @property
    def items_on_page(self):
        if self.islastpage:
            remainder = self.sequence_length % self.pagesize
            if remainder == 0:
                return self.pagesize
            else:
                return remainder
        else:
            return self.pagesize

    @property
    def multiple_pages(self):
        return bool(self.sequence_length / self.pagesize)

    @property
    def previouspage(self):
        return self.pagenumber - 1

    @property
    def nextpage(self):
        return self.pagenumber + 1

    @property
    def items_not_on_page(self):
        return self._sequence[:self.start] + self._sequence[self.end:]

    @property
    def next_item_count(self):
        """
        Number of elements in next batch
        """
        return self.next.length

    @property
    def has_next(self):
        return self.next is not None

    @property
    def show_link_to_first(self):
        return 1 not in self.navlist

    @property
    def show_link_to_last(self):
        return self.lastpage not in self.navlist

    @property
    def before_last_page_not_in_navlist(self):
        return (self.lastpage - 1) not in self.navlist

    @property
    def has_previous(self):
        return self.pagenumber > 1

    @property
    def previous_pages(self):
        return self.navlist[:self.navlist.index(self.pagenumber)]

    @property
    def next_pages(self):
        return self.navlist[self.navlist.index(self.pagenumber) + 1:]

    @property
    def second_page_not_in_navlist(self):
        return 2 not in self.navlist


class QuantumBatch(BaseBatch):
    quantumleap = False
    leapback = []
    leapforward = []

    def __init__(self, sequence, size, start=0, end=0, orphan=0, overlap=0, pagerange=7, quantumleap=0):
        """
        quantumleap - 0 or 1 to indicate if bigger increments should be used in the navigation list for big results.
        b_start_str - the request variable used for start, default 'b_start'
        """
        super(QuantumBatch, self).__init__(sequence, size, start, end, orphan, overlap, pagerange)
        self.quantumleap = quantumleap

    def initialize(self, start, end, size):
        super(QuantumBatch, self).initialize(start, end, size)
        if self.quantumleap:
            self.leapback = calculate_leapback(self.pagenumber, self.numpages, self.pagerange)
            self.leapforward = calculate_leapforward(self.pagenumber, self.numpages, self.pagerange)

Batch = BaseBatch