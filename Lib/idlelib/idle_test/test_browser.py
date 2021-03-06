""" Test idlelib.browser.

Coverage: 88%
(Higher, because should exclude 3 lines that .coveragerc won't exclude.)
"""

import os.path
import unittest
import pyclbr

from idlelib import browser, filelist
from idlelib.tree import TreeNode
from test.support import requires
from unittest import mock
from tkinter import Tk
from idlelib.idle_test.mock_idle import Func
from collections import deque


class ClassBrowserTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        requires('gui')
        cls.root = Tk()
        cls.root.withdraw()
        cls.flist = filelist.FileList(cls.root)
        cls.file = __file__
        cls.path = os.path.dirname(cls.file)
        cls.module = os.path.basename(cls.file).rstrip('.py')
        cls.cb = browser.ClassBrowser(cls.flist, cls.module, [cls.path], _utest=True)

    @classmethod
    def tearDownClass(cls):
        cls.cb.close()
        cls.root.destroy()
        del cls.root, cls.flist, cls.cb

    def test_init(self):
        cb = self.cb
        eq = self.assertEqual
        eq(cb.name, self.module)
        eq(cb.file, self.file)
        eq(cb.flist, self.flist)
        eq(pyclbr._modules, {})
        self.assertIsInstance(cb.node, TreeNode)

    def test_settitle(self):
        cb = self.cb
        self.assertIn(self.module, cb.top.title())
        self.assertEqual(cb.top.iconname(), 'Class Browser')

    def test_rootnode(self):
        cb = self.cb
        rn = cb.rootnode()
        self.assertIsInstance(rn, browser.ModuleBrowserTreeItem)

    def test_close(self):
        cb = self.cb
        cb.top.destroy = Func()
        cb.node.destroy = Func()
        cb.close()
        self.assertTrue(cb.top.destroy.called)
        self.assertTrue(cb.node.destroy.called)
        del cb.top.destroy, cb.node.destroy


# Same nested tree creation as in test_pyclbr.py except for super on C0.
mb = pyclbr
module, fname = 'test', 'test.py'
f0 = mb.Function(module, 'f0', fname, 1)
f1 = mb._nest_function(f0, 'f1', 2)
f2 = mb._nest_function(f1, 'f2', 3)
c1 = mb._nest_class(f0, 'c1', 5)
C0 = mb.Class(module, 'C0', ['base'], fname, 6)
F1 = mb._nest_function(C0, 'F1', 8)
C1 = mb._nest_class(C0, 'C1', 11, [''])
C2 = mb._nest_class(C1, 'C2', 12)
F3 = mb._nest_function(C2, 'F3', 14)
mock_pyclbr_tree = {'f0': f0, 'C0': C0}

# transform_children(mock_pyclbr_tree, 'test') mutates C0.name.

class TransformChildrenTest(unittest.TestCase):

    def test_transform_children(self):
        eq = self.assertEqual
        # Parameter matches tree module.
        tcl = list(browser.transform_children(mock_pyclbr_tree, 'test'))
        eq(tcl[0], f0)
        eq(tcl[1], C0)
        eq(tcl[1].name, 'C0(base)')
        # Check that second call does not add second '(base)' suffix.
        tcl = list(browser.transform_children(mock_pyclbr_tree, 'test'))
        eq(tcl[1].name, 'C0(base)')
        # Nothing to traverse if parameter name isn't same as tree module.
        tn = browser.transform_children(mock_pyclbr_tree, 'different name')
        self.assertEqual(list(tn), [])
        # No name parameter.
        tn = browser.transform_children({'f1': f1, 'c1': c1})
        self.assertEqual(list(tn), [f1, c1])


class ModuleBrowserTreeItemTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.mbt = browser.ModuleBrowserTreeItem(fname)

    def test_init(self):
        self.assertEqual(self.mbt.file, fname)

    def test_gettext(self):
        self.assertEqual(self.mbt.GetText(), fname)

    def test_geticonname(self):
        self.assertEqual(self.mbt.GetIconName(), 'python')

    def test_isexpandable(self):
        self.assertTrue(self.mbt.IsExpandable())

    def test_listchildren(self):
        save_rex = browser.pyclbr.readmodule_ex
        save_tc = browser.transform_children
        browser.pyclbr.readmodule_ex = Func(result=mock_pyclbr_tree)
        browser.transform_children = Func(result=[f0, C0])
        try:
            self.assertEqual(self.mbt.listchildren(), [f0, C0])
        finally:
            browser.pyclbr.readmodule_ex = save_rex
            browser.transform_children = save_tc

    def test_getsublist(self):
        mbt = self.mbt
        mbt.listchildren = Func(result=[f0, C0])
        sub0, sub1 = mbt.GetSubList()
        del mbt.listchildren
        self.assertIsInstance(sub0, browser.ChildBrowserTreeItem)
        self.assertIsInstance(sub1, browser.ChildBrowserTreeItem)
        self.assertEqual(sub0.name, 'f0')
        self.assertEqual(sub1.name, 'C0')


    def test_ondoubleclick(self):
        mbt = self.mbt
        fopen = browser.file_open = mock.Mock()

        with mock.patch('os.path.exists', return_value=False):
            mbt.OnDoubleClick()
            fopen.assert_not_called()

        with mock.patch('os.path.exists', return_value=True):
            mbt.OnDoubleClick()
            fopen.assert_called()
            fopen.called_with(fname)

        del browser.file_open


class ChildBrowserTreeItemTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        CBT = browser.ChildBrowserTreeItem
        cls.cbt_f1 = CBT(f1)
        cls.cbt_C1 = CBT(C1)
        cls.cbt_F1 = CBT(F1)

    @classmethod
    def tearDownClass(cls):
        del cls.cbt_C1, cls.cbt_f1, cls.cbt_F1

    def test_init(self):
        eq = self.assertEqual
        eq(self.cbt_C1.name, 'C1')
        self.assertFalse(self.cbt_C1.isfunction)
        eq(self.cbt_f1.name, 'f1')
        self.assertTrue(self.cbt_f1.isfunction)

    def test_gettext(self):
        self.assertEqual(self.cbt_C1.GetText(), 'class C1')
        self.assertEqual(self.cbt_f1.GetText(), 'def f1(...)')

    def test_geticonname(self):
        self.assertEqual(self.cbt_C1.GetIconName(), 'folder')
        self.assertEqual(self.cbt_f1.GetIconName(), 'python')

    def test_isexpandable(self):
        self.assertTrue(self.cbt_C1.IsExpandable())
        self.assertTrue(self.cbt_f1.IsExpandable())
        self.assertFalse(self.cbt_F1.IsExpandable())

    def test_getsublist(self):
        eq = self.assertEqual
        CBT = browser.ChildBrowserTreeItem

        f1sublist = self.cbt_f1.GetSubList()
        self.assertIsInstance(f1sublist[0], CBT)
        eq(len(f1sublist), 1)
        eq(f1sublist[0].name, 'f2')

        eq(self.cbt_F1.GetSubList(), [])

    def test_ondoubleclick(self):
        fopen = browser.file_open = mock.Mock()
        goto = fopen.return_value.gotoline = mock.Mock()
        self.cbt_F1.OnDoubleClick()
        fopen.assert_called()
        goto.assert_called()
        goto.assert_called_with(self.cbt_F1.obj.lineno)
        del browser.file_open
        # Failure test would have to raise OSError or AttributeError.


class NestedChildrenTest(unittest.TestCase):
    "Test that all the nodes in a nested tree are added to the BrowserTree."

    def test_nested(self):
        queue = deque()
        actual_names = []
        # The tree items are processed in breadth first order.
        # Verify that processing each sublist hits every node and
        # in the right order.
        expected_names = ['f0', 'C0',  # This is run before transform test.
                          'f1', 'c1', 'F1', 'C1()',
                          'f2', 'C2',
                          'F3']
        CBT = browser.ChildBrowserTreeItem
        queue.extend((CBT(f0), CBT(C0)))
        while queue:
            cb = queue.popleft()
            sublist = cb.GetSubList()
            queue.extend(sublist)
            self.assertIn(cb.name, cb.GetText())
            self.assertIn(cb.GetIconName(), ('python', 'folder'))
            self.assertIs(cb.IsExpandable(), sublist != [])
            actual_names.append(cb.name)
        self.assertEqual(actual_names, expected_names)


if __name__ == '__main__':
    unittest.main(verbosity=2)
