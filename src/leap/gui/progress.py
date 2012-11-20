"""
classes used in progress pages
from first run wizard
"""
try:
    from collections import OrderedDict
except ImportError:
    # We must be in 2.6
    from leap.util.dicts import OrderedDict

import logging

from PyQt4 import QtCore
from PyQt4 import QtGui

from leap.gui.threads import FunThread

from leap.gui import mainwindow_rc

ICON_CHECKMARK = ":/images/Dialog-accept.png"
ICON_FAILED = ":/images/Dialog-error.png"
ICON_WAITING = ":/images/Emblem-question.png"

logger = logging.getLogger(__name__)


class ImgWidget(QtGui.QWidget):

    # XXX move to widgets

    def __init__(self, parent=None, img=None):
        super(ImgWidget, self).__init__(parent)
        self.pic = QtGui.QPixmap(img)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.drawPixmap(0, 0, self.pic)


class ProgressStep(object):
    """
    Data model for sequential steps
    to be used in a progress page in
    connection wizard
    """
    NAME = 0
    DONE = 1

    def __init__(self, stepname, done, index=None):
        """
        @param step: the name of  the step
        @type step: str
        @param done: whether is completed or not
        @type done: bool
        """
        self.index = int(index) if index else 0
        self.name = unicode(stepname)
        self.done = bool(done)

    @classmethod
    def columns(self):
        return ('name', 'done')


class ProgressStepContainer(object):
    """
    a container for ProgressSteps objects
    access data in the internal dict
    """

    def __init__(self):
        self.dirty = False
        self.steps = {}

    def step(self, identity):
        return self.step.get(identity)

    def addStep(self, step):
        self.steps[step.index] = step

    def removeStep(self, step):
        del self.steps[step.index]
        del step
        self.dirty = True

    def removeAllSteps(self):
        for item in iter(self):
            self.removeStep(item)

    @property
    def columns(self):
        return ProgressStep.columns()

    def __len__(self):
        return len(self.steps)

    def __iter__(self):
        for step in self.steps.values():
            yield step


class StepsTableWidget(QtGui.QTableWidget):
    """
    initializes a TableWidget
    suitable for our display purposes, like removing
    header info and grid display
    """

    def __init__(self, parent=None):
        super(StepsTableWidget, self).__init__(parent)

        # remove headers and all edit/select behavior
        self.horizontalHeader().hide()
        self.verticalHeader().hide()
        self.setEditTriggers(
            QtGui.QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(
            QtGui.QAbstractItemView.NoSelection)
        width = self.width()
        # WTF? Here init width is 100...
        # but on populating is 456... :(

        # XXX do we need this initial?
        logger.debug('init table. width=%s' % width)
        self.horizontalHeader().resizeSection(0, width * 0.7)

        # this disables the table grid.
        # we should add alignment to the ImgWidget (it's top-left now)
        self.setShowGrid(False)

        # XXX change image for done to rc

        # Note about the "done" status painting:
        #
        # XXX currently we are setting the CellWidget
        # for the whole table on a per-row basis
        # (on add_status_line method on ValidationPage).
        # However, a more generic solution might be
        # to implement a custom Delegate that overwrites
        # the paint method (so it paints a checked tickmark if
        # done is True and some other thing if checking or false).
        # What we have now is quick and works because
        # I'm supposing that on first fail we will
        # go back to previous wizard page to signal the failure.
        # A more generic solution could be used for
        # some failing tests if they are not critical.


class WithStepsMixIn(object):

    def connect_step_status(self):
        self.stepChanged.connect(
            self.onStepStatusChanged)

    def connect_failstep_status(self):
        self.stepFailed.connect(
            self.set_failed_icon)

    # slot
    #@QtCore.pyqtSlot(str, int)
    def onStepStatusChanged(self, status, progress=None):
        if status not in ("head_sentinel", "end_sentinel"):
            self.add_status_line(status)
        if status in ("end_sentinel"):
            self.checks_finished = True
            self.set_checked_icon()
        if progress and hasattr(self, 'progress'):
            self.progress.setValue(progress)
            self.progress.update()

    def setupSteps(self):
        self.steps = ProgressStepContainer()
        # steps table widget
        self.stepsTableWidget = StepsTableWidget(self)
        zeros = (0, 0, 0, 0)
        self.stepsTableWidget.setContentsMargins(*zeros)
        self.errors = OrderedDict()

    def set_error(self, name, error):
        self.errors[name] = error

    def pop_first_error(self):
        return list(reversed(self.errors.items())).pop()

    def clean_errors(self):
        self.errors = OrderedDict()

    def clean_wizard_errors(self, pagename=None):
        if pagename is None:
            pagename = getattr(self, 'prev_page', None)
        if pagename is None:
            return
        logger.debug('cleaning wizard errors for %s' % pagename)
        self.wizard().set_validation_error(pagename, None)

    def populateStepsTable(self):
        # from examples,
        # but I guess it's not needed to re-populate
        # the whole table.
        table = self.stepsTableWidget
        table.setRowCount(len(self.steps))
        columns = self.steps.columns
        table.setColumnCount(len(columns))

        for row, step in enumerate(self.steps):
            item = QtGui.QTableWidgetItem(step.name)
            item.setData(QtCore.Qt.UserRole,
                         long(id(step)))
            table.setItem(row, columns.index('name'), item)
            table.setItem(row, columns.index('done'),
                          QtGui.QTableWidgetItem(step.done))
        self.resizeTable()
        self.update()

    def clearTable(self):
        # ??? -- not sure what's the difference
        #self.stepsTableWidget.clear()
        self.stepsTableWidget.clearContents()

    def resizeTable(self):
        # resize first column to ~80%
        table = self.stepsTableWidget
        FIRST_COLUMN_PERCENT = 0.75
        width = table.width()
        logger.debug('populate table. width=%s' % width)
        table.horizontalHeader().resizeSection(0, width * FIRST_COLUMN_PERCENT)

    def set_item_icon(self, img=ICON_CHECKMARK, current=True):
        """
        mark the last item
        as done
        """
        # setting cell widget.
        # see note on StepsTableWidget about plans to
        # change this for a better solution.
        index = len(self.steps)
        table = self.stepsTableWidget
        _index = index - 1 if current else index - 2
        table.setCellWidget(
            _index,
            ProgressStep.DONE,
            ImgWidget(img=img))
        table.update()

    def set_failed_icon(self):
        self.set_item_icon(img=ICON_FAILED, current=True)

    def set_checking_icon(self):
        self.set_item_icon(img=ICON_WAITING, current=True)

    def set_checked_icon(self, current=True):
        self.set_item_icon(current=current)

    def add_status_line(self, message):
        """
        adds a new status line
        and mark the next-to-last item
        as done
        """
        index = len(self.steps)
        step = ProgressStep(message, False, index=index)
        self.steps.addStep(step)
        self.populateStepsTable()
        self.set_checking_icon()
        self.set_checked_icon(current=False)


"""
Resist the temptation to refactor the declaration of the signal
to the mixin.
PyQt and multiple inheritance do not mix well together.
You can only have one QObject base.
Therefore, we will use one base class for the intermediate pages
and another one for the in-page validations, both sharing the creation
of the tablewidgets.
"""


class InlineValidationPage(QtGui.QWizardPage, WithStepsMixIn):

    # signals
    stepChanged = QtCore.pyqtSignal([str, int])
    stepFailed = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(InlineValidationPage, self).__init__(parent)
        self.connect_step_status()
        self.connect_failstep_status()

    def do_checks(self):
        """
        launches a thread to do the checks
        """
        beupdate = self.stepChanged
        befailed = self.stepFailed
        self.checks = FunThread(
            self._do_checks(update_signal=beupdate, failed_signal=befailed))
        self.checks.finished.connect(self._inline_validation_ready)
        self.checks.begin()
        #self.checks.wait()


class ValidationPage(QtGui.QWizardPage, WithStepsMixIn):
    """
    class to be used as an intermediate
    between two pages in a wizard.
    shows feedback to the user and goes back if errors,
    goes forward if ok.
    initializePage triggers a one shot timer
    that calls do_checks.
    Derived classes should implement
    _do_checks and
    _do_validation
    """

    # signals
    stepChanged = QtCore.pyqtSignal([str, int])

    def __init__(self, parent=None):
        super(ValidationPage, self).__init__(parent)
        self.setupSteps()
        self.connect_step_status()

        layout = QtGui.QVBoxLayout()
        self.progress = QtGui.QProgressBar(self)
        layout.addWidget(self.progress)
        layout.addWidget(self.stepsTableWidget)

        self.setLayout(layout)
        self.layout = layout

        self.timer = QtCore.QTimer()

        self.done = False

    # Sets/unsets done flag
    # for isComplete checks

    def set_done(self):
        self.done = True
        self.completeChanged.emit()

    def set_undone(self):
        self.done = False
        self.completeChanged.emit()

    def is_done(self):
        return self.done

    def isComplete(self):
        return self.is_done()

    ########################

    def go_back(self):
        self.wizard().back()

    def go_next(self):
        self.wizard().next()

    def do_checks(self):
        """
        launches a thread to do the checks
        """
        signal = self.stepChanged
        self.checks = FunThread(
            self._do_checks(update_signal=signal))
        self.checks.finished.connect(self._do_validation)
        self.checks.begin()
        #logger.debug('check thread started!')
        #logger.debug('waiting for it to terminate...')
        self.checks.wait()

    def show_progress(self):
        self.progress.show()
        self.stepsTableWidget.show()

    def hide_progress(self):
        self.progress.hide()
        self.stepsTableWidget.hide()

    # pagewizard methods.
    # if overriden, child classes should call super.

    def initializePage(self):
        self.clean_errors()
        self.clean_wizard_errors()
        self.steps.removeAllSteps()
        self.clearTable()
        self.resizeTable()
        self.timer.singleShot(0, self.do_checks)
