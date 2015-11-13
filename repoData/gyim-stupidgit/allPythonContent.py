__FILENAME__ = AboutDialog
# -*- coding: utf-8
import wx

STUPIDGIT_VERSION = "v0.1.1"

license_text = u'''
Copyright (c) 2009 Ákos Gyimesi

Permission is hereby granted, free of charge, to
any person obtaining a copy of this software and
associated documentation files (the "Software"),
to deal in the Software without restriction,
including without limitation the rights to use,
copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software,
and to permit persons to whom the Software is
furnished to do so, subject to the following
conditions:

The above copyright notice and this permission
notice shall be included in all copies or
substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY
OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT
LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT.  IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
OR OTHER LIABILITY, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF
OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
'''

def ShowAboutDialog():
    info = wx.AboutDialogInfo()
    info.SetName("stupidgit")
    info.SetDescription("A cross-platform git GUI with strong submodule support.\n\nHomepage: http://github.com/gyim/stupidgit")
    info.SetVersion(STUPIDGIT_VERSION)
    info.SetCopyright(u"(c) Ákos Gyimesi, 2009.")
    info.SetLicense(license_text)

    wx.AboutBox(info)

########NEW FILE########
__FILENAME__ = CommitList
import wx
import git
import platformspec
from util import *

COLW  = 12 # Column width
LINH  = 16 # Line height
COMW  = 8  # Commit width

EDGE_COLORS = [
    (  0,   0,  96, 200),
    (  0,  96,   0, 200),
    ( 96,   0,   0, 200),

    ( 64,  64,   0, 200),
    ( 64,  0,   64, 200),
    (  0,  64,  64, 200),

    (128, 192,   0, 200),
    (192, 128,   0, 200),
    ( 64,   0, 128, 200),
    (  0, 160,  96, 200),
    (  0,  96, 160, 200)
]

class CommitList(wx.ScrolledWindow):
    def __init__(self, parent, id, allowMultiple=False):
        wx.ScrolledWindow.__init__(self, parent, -1, style=wx.SUNKEN_BORDER)
        self.SetBackgroundColour('WHITE')
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftClick)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftRelease)
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightClick)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyPressed)
        self.Bind(wx.EVT_MOTION, self.OnMouseMove)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseLeave)
        self.repo = None
        self.rows = []
        self.selection = []
        self.mainRepo = None
        self.mainRepoSelection = []
        self.allowMultiple = allowMultiple
        self.authorColumnPos = 200
        
        self.normalCursor = wx.NullCursor
        self.resizeCursor = wx.StockCursor(wx.CURSOR_SIZEWE)
        self.currentCursor = self.normalCursor
        self.resizing = False

    def SetRepo(self, repo):
        # Save selection if the last repo was the main repo
        if self.repo and self.repo == self.mainRepo:
            self.mainRepo = self.repo
            self.mainRepoSelection = [ self.rows[row][0].commit.sha1 for row in self.selection ]

        # Clear selection, scroll to top
        repo_changed = (self.repo != repo)
        if repo_changed:
            self.selection = []
            self.Scroll(0, 0)

        # Save main repo
        if not repo.parent:
            self.mainRepo = repo

        # Load commits
        self.repo = repo
        self.commits = self.repo.get_log(['--topo-order', '--all'])
        self.CreateLogGraph()

        # If this is a submodule, select versions that are referenced
        # by the parent module
        if repo_changed and self.repo != self.mainRepo:
            for version in self.mainRepoSelection:
                submodule_version = self.repo.parent.get_submodule_version(self.repo.name, version)
                if submodule_version:
                    rows = [ r for r in self.rows if r[0].commit.sha1 == submodule_version ]
                    if rows:
                        self.selection.append(self.rows.index(rows[0]))

        # Setup UI
        self.SetVirtualSize((-1, (len(self.rows)+1) * LINH))
        self.SetScrollRate(LINH, LINH)
        self.Refresh()
    
    def CreateLogGraph(self):
        rows = []  # items: (node, edges)
        nodes = {} # commit => GraphNode
        lanes = []
        color = 0

        self.rows = rows
        self.columns = 0
        self.nodes = nodes
        
        for y in xrange(len(self.commits)):
            # 1. Create node
            commit = self.commits[y]
            node = GraphNode(commit)
            nodes[commit] = node
            node.y = y
            rows.append((node, []))

            # 2. Determine column
            x = None

            # 2.1. search for a commit in lanes whose parent is c
            for i in xrange(len(lanes)):
                if lanes[i] and commit in lanes[i].commit.parents:
                    x = i
                    node.color = lanes[i].color
                    break

            # 2.2. if there is no such commit, put to the first empty place
            if x == None:
                node.color = color
                color += 1
                if None in lanes:
                    x = lanes.index(None)
                else:
                    x = len(lanes)
                    lanes.append(None)

            node.x = x
            self.columns = max(self.columns, x)

            # 3. Create edges
            for child_commit in commit.children:
                child = nodes[child_commit]
                edge = GraphEdge(node, child)
                node.child_edges.append(edge)
                child.parent_edges.append(edge)

                # 3.1. Determine edge style
                if child.x == node.x and lanes[x] == child:
                    edge.style = EDGE_DIRECT
                    edge.x = node.x
                    edge.color = child.color
                elif len(child_commit.parents) == 1:
                    edge.style = EDGE_BRANCH
                    edge.x = child.x
                    edge.color = child.color
                else:
                    edge.style = EDGE_MERGE
                    edge.color = node.color

                    # Determine column for merge edges
                    edge.x = max(node.x, child.x+1)
                    success = False
                    while not success:
                        success = True
                        for yy in xrange(node.y, child.y, -1):
                            n, edges = rows[yy]
                            if (yy < node.y and n.x == edge.x) or (len(edges) > edge.x and edges[edge.x] != None):
                                edge.x += 1
                                success = False
                                break

                # 3.2. Register edge in rows
                for yy in xrange(node.y, child.y, -1):
                    n, edges = rows[yy]
                    if len(edges) < edge.x+1:
                        edges += [None] * (edge.x+1 - len(edges))
                    edges[edge.x] = edge

                self.columns = max(self.columns, edge.x)

            # 4. End those lanes whose parents are already drawn
            for i in xrange(len(lanes)):
                if lanes[i] and len(lanes[i].parent_edges) == len(lanes[i].commit.parents):
                    lanes[i] = None

            lanes[x] = node

        # References
        if self.repo.current_branch:
            self._add_reference(self.repo.head, self.repo.current_branch, REF_HEADBRANCH)
        else:
            self._add_reference(self.repo.head, 'DETACHED HEAD', REF_DETACHEDHEAD)

        if self.repo.main_ref:
            self._add_reference(self.repo.main_ref, 'MAIN/HEAD', REF_MODULE)
        if self.repo.main_merge_ref:
            self._add_reference(self.repo.main_merge_ref, 'MAIN/MERGE_HEAD', REF_MODULE)

        for branch,commit_id in self.repo.branches.iteritems():
            if branch != self.repo.current_branch:
                self._add_reference(commit_id, branch, REF_BRANCH)
        for branch,commit_id in self.repo.remote_branches.iteritems():
            self._add_reference(commit_id, branch, REF_REMOTE)
        for tag,commit_id in self.repo.tags.iteritems():
            self._add_reference(commit_id, tag, REF_TAG)

    def _add_reference(self, commit_id, refname, reftype):
        if commit_id not in git.commit_pool:
            return

        commit = git.commit_pool[commit_id]
        if commit not in self.nodes:
            return

        self.nodes[commit].references.append((refname, reftype))

    def OnPaint(self, evt):
        evt.Skip(False)

        if not self.repo:
            return

        # Setup drawing context
        pdc = wx.PaintDC(self)
        try:
            dc = wx.GCDC(pdc)
        except:
            dc = pdc

        dc.BeginDrawing()
        
        # Get basic drawing context details
        size = self.GetClientSize()
        clientWidth, clientHeight = size.GetWidth(), size.GetHeight()

        # Determine which commits to draw
        x, y, width, height = self.GetUpdateRegion().GetBox()
        start_x, start_y = self.CalcUnscrolledPosition(x, y)
        start_row, end_row = max(0, start_y/LINH-1), (start_y+height)/LINH+1

        # Setup pens, brushes and fonts
        commit_pen = wx.Pen(wx.Colour(0,0,0,255), width=2)
        commit_brush = wx.Brush(wx.Colour(255,255,255,255))
        commit_font = platformspec.Font(12)

        commit_textcolor_normal = wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOWTEXT)
        commit_textcolor_highlight = wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)

        edge_pens = [ wx.Pen(wx.Colour(*c), width=2) for c in EDGE_COLORS ]

        background_pen = wx.NullPen
        background_brush = wx.Brush(wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOW))

        selection_pen = wx.NullPen
        selection_brush = wx.Brush(wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHT))
        
        separator_pen = wx.Pen(wx.SystemSettings_GetColour(wx.SYS_COLOUR_3DLIGHT), width=1)

        ref_pens = [
            wx.Pen(wx.Colour(128,128,192,255), width=1),   # REF_BRANCH
            wx.Pen(wx.Colour(0,255,0,255), width=1),       # REF_REMOTE
            wx.Pen(wx.Colour(128,128,0,255), width=1),     # REF_TAG
            wx.Pen(wx.Colour(255,128,128,255), width=1),   # REF_HEADBRANCH
            wx.Pen(wx.Colour(255,0,0,255), width=1),       # REF_DETACHEDHEAD
            wx.Pen(wx.Colour(160,160,160,255), width=1)    # REF_MODULE
        ]
        ref_brushes = [
            wx.Brush(wx.Colour(160,160,255,255)), # REF_BRANCH
            wx.Brush(wx.Colour(128,255,128,255)), # REF_REMOTE
            wx.Brush(wx.Colour(255,255,128,255)), # REF_TAG
            wx.Brush(wx.Colour(255,160,160,255)), # REF_HEADBRANCH
            wx.Brush(wx.Colour(255,128,128,255)), # REF_DETACHEDHEAD
            wx.Brush(wx.Colour(192,192,192,255))  # REF_MODULE
        ]
        ref_font = platformspec.Font(9)
        ref_textcolor = wx.Colour(0,0,0,255)

        # Draw selection
        dc.SetPen(selection_pen)
        dc.SetBrush(selection_brush)
        for row in self.selection:
            if start_row <= row <= end_row:
                x, y = self.CalcScrolledPosition(0, (row+1)*LINH)
                dc.DrawRectangle(0, y-LINH/2, clientWidth, LINH)

        # Offsets
        offx = COLW
        offy = LINH

        # Draw edges
        edges = set()
        for node,row_edges in self.rows[start_row:end_row+1]:
            edges.update(row_edges)
        for edge in edges:
            if not edge: continue

            dc.SetPen(edge_pens[edge.color % len(EDGE_COLORS)])
            if edge.style == EDGE_DIRECT:
                x1, y1 = self.CalcScrolledPosition( edge.src.x*COLW+offx, edge.src.y*LINH+offy )
                x2, y2 = self.CalcScrolledPosition( edge.dst.x*COLW+offx, edge.dst.y*LINH+offy )
                dc.DrawLine(x1, y1, x2, y2)
            elif edge.style == EDGE_BRANCH:
                x1, y1 = self.CalcScrolledPosition( edge.src.x*COLW+offx, edge.src.y*LINH+offy )
                x2, y2 = self.CalcScrolledPosition( edge.dst.x*COLW+offx, edge.src.y*LINH+offy-7 )
                x3, y3 = self.CalcScrolledPosition( edge.dst.x*COLW+offx, edge.dst.y*LINH+offy )
                dc.DrawLine(x1, y1, x2, y2)
                dc.DrawLine(x2, y2, x3, y3)
            elif edge.style == EDGE_MERGE:
                x1, y1 = self.CalcScrolledPosition( edge.src.x*COLW+offx, edge.src.y*LINH+offy )
                x2, y2 = self.CalcScrolledPosition( edge.x*COLW+offx, edge.src.y*LINH+offy-7 )
                x3, y3 = self.CalcScrolledPosition( edge.x*COLW+offx, edge.dst.y*LINH+offy+7 )
                x4, y4 = self.CalcScrolledPosition( edge.dst.x*COLW+offx, edge.dst.y*LINH+offy )
                dc.DrawLine(x1, y1, x2, y2)
                dc.DrawLine(x2, y2, x3, y3)
                dc.DrawLine(x3, y3, x4, y4)

        # Draw commits
        dc.SetPen(commit_pen)
        dc.SetBrush(commit_brush)
        for node,edges in self.rows[start_row:end_row+1]:
            # Background pen & brush
            if self.rows.index((node, edges)) in self.selection:
                commit_bg_pen = selection_pen
                commit_bg_brush = selection_brush
            else:
                commit_bg_pen = background_pen
                commit_bg_brush = background_brush

            # Draw commit circle/rectangle
            if node.style == NODE_MERGE:
                x = node.x*COLW + offx - COMW/2
                y = node.y*LINH + offy - COMW/2   
                xx, yy = self.CalcScrolledPosition(x, y)
                dc.DrawRectangle(xx, yy, COMW, COMW)
            else:
                x = node.x*COLW + offx
                y = node.y*LINH + offy
                xx, yy = self.CalcScrolledPosition(x, y)
                dc.DrawCircle(xx, yy, COMW/2)

            # Calculate column
            if node.y < len(self.rows)-1:
                text_column = max(len(edges), len(self.rows[node.y+1][1]))
            else:
                text_column = len(edges) if len(edges) > 0 else 1

            # Draw references
            msg_offset = 0

            for refname,reftype in node.references:
                dc.SetPen(ref_pens[reftype])
                dc.SetBrush(ref_brushes[reftype])
                dc.SetFont(ref_font)
                dc.SetTextForeground(ref_textcolor)

                x = text_column*COLW + offx + msg_offset
                y = node.y*LINH + offy - LINH/2 + 1
                width,height = dc.GetTextExtent(refname)
                
                if reftype in [REF_HEADBRANCH, REF_DETACHEDHEAD, REF_MODULE]:
                    points = [
                        (x, y+LINH/2-1),
                        (x+6, y),
                        (x+10 + width, y),
                        (x+10 + width, y+LINH-3),
                        (x+6, y+LINH-3)
                    ]
                    x += 6
                    points = [ self.CalcScrolledPosition(*p) for p in points ]
                    points = [ wx.Point(*p) for p in points ]

                    dc.DrawPolygon(points)
                    msg_offset += width+14
                else:
                    xx, yy = self.CalcScrolledPosition(x, y)
                    dc.DrawRoundedRectangle(xx, yy, width + 4, LINH-2, 2)
                    msg_offset += width+8

                dc.SetPen(commit_pen)
                dc.SetBrush(commit_brush)
                xx, yy = self.CalcScrolledPosition(x+2, y+1)
                dc.DrawText(safe_unicode(refname), xx, yy)

            # Draw message
            dc.SetFont(commit_font)
            x = text_column*COLW + offx + msg_offset
            y = node.y*LINH + offy - LINH/2
            xx, yy = self.CalcScrolledPosition(x, y)
            
            if self.rows.index((node, edges)) in self.selection:
                dc.SetTextForeground(commit_textcolor_highlight)
            else:
                dc.SetTextForeground(commit_textcolor_normal)

            dc.DrawText(safe_unicode(node.commit.short_msg), xx, yy)
            
            # Draw author & date
            x = clientWidth - self.authorColumnPos
            
            dc.SetBrush(commit_bg_brush)
            
            dc.SetPen(commit_bg_pen)
            xx, yy = self.CalcScrolledPosition(x, y)
            dc.DrawRectangle(xx-4, yy, clientWidth-x+4, LINH)
            
            dc.SetPen(separator_pen)
            dc.DrawLine(xx, yy, xx, yy+LINH)
            
            dc.SetPen(commit_pen)
            dc.SetBrush(commit_brush)
            author_text = u'%s, %s' % (safe_unicode(node.commit.author_name), safe_unicode(node.commit.author_date))
            dc.DrawText(author_text, xx+4, yy)

        dc.EndDrawing()

    def OnMouseMove(self, e):
        if self.resizing:
            self.authorColumnPos = self.GetClientSize().GetWidth() - e.m_x
            self.Refresh()
        else:
            pos = self.GetClientSize().GetWidth() - self.authorColumnPos
            if pos-2 <= e.m_x <= pos+2:
                if self.currentCursor != self.resizeCursor:
                    self.SetCursor(self.resizeCursor)
                    self.currentCursor = self.resizeCursor
            else:
                if self.currentCursor != self.normalCursor:
                    self.SetCursor(self.normalCursor)
                    self.currentCursor = self.normalCursor

    def OnLeftClick(self, e):
        e.StopPropagation()
        self.SetFocus()
        
        # Column resize
        if self.currentCursor == self.resizeCursor:
            self.resizing = True
            return

        # Determine row number
        x, y = self.CalcUnscrolledPosition(*(e.GetPosition()))
        row = self.RowNumberByCoords(x, y)
        if row == None:
            return

        # Handle different type of clicks
        old_selection = list(self.selection)
        if self.allowMultiple and e.ShiftDown() and len(old_selection) >= 1:
            from_row = old_selection[0]
            to_row = row
            if to_row >= from_row:
                self.selection = range(from_row, to_row+1)
            else:
                self.selection = range(to_row, from_row+1)
                self.selection.reverse()
        elif self.allowMultiple and (e.ControlDown() or e.CmdDown()):
            if row not in self.selection:
                self.selection.insert(0, row)
        else:
            self.selection = [row]

        # Emit click event
        event = CommitListEvent(EVT_COMMITLIST_SELECT_type, self.GetId())
        event.SetCurrentRow(row)
        event.SetSelection(self.selection)
        self.ProcessEvent(event)
        self.OnSelectionChanged(row, self.selection)

        # Redraw window
        self.Refresh()

    def OnLeftRelease(self, e):
        e.StopPropagation()
        self.resizing = False

    def OnMouseLeave(self, e):
        e.StopPropagation()
        self.resizing = False

    def OnRightClick(self, e):
        e.StopPropagation()
        self.SetFocus()

        # Determine row number
        x, y = self.CalcUnscrolledPosition(*(e.GetPosition()))
        row = self.RowNumberByCoords(x, y)
        if row == None:
            return
        
        self.SelectRow(row)

        # Emit right click event
        event = CommitListEvent(EVT_COMMITLIST_RIGHTCLICK_type, self.GetId())
        event.SetCurrentRow(row)
        event.SetSelection(self.selection)
        event.SetCoords( (e.GetX(), e.GetY()) )
        self.ProcessEvent(event)
        self.OnRightButtonClicked(row, self.selection)
        
    def OnKeyPressed(self, e):
        key = e.GetKeyCode()

        # Handle only UP and DOWN keys
        if key not in [wx.WXK_UP, wx.WXK_DOWN] or len(self.rows) == 0:
            e.Skip()
            return

        e.StopPropagation()

        # Get scrolling position
        start_col, start_row = self.GetViewStart()
        size = self.GetClientSize()
        height = size.GetHeight() / LINH

        if self.selection:
            # Process up/down keys
            current_row = self.selection[0]

            if key == wx.WXK_UP:
                next_row = max(current_row-1, 0)
            if key == wx.WXK_DOWN:
                next_row = min(current_row+1, len(self.rows)-1)

            # Process modifiers
            if e.ShiftDown() and self.allowMultiple:
                if next_row in self.selection:
                    self.selection.remove(current_row)
                else:
                    self.selection.insert(0, next_row)
            else:
                self.selection = [next_row]

        else:
            # Select topmost row of current view
            next_row = start_row
            if next_row < 0 or next_row > len(self.rows):
                return

            self.selection = [next_row]

        # Scroll selection if necessary
        if next_row < start_row:
            self.Scroll(start_col, next_row-1)
        elif next_row > start_row + height - 1:
            self.Scroll(start_col, next_row-height+2)

        # Emit selection event
        event = CommitListEvent(EVT_COMMITLIST_SELECT_type, self.GetId())
        event.SetCurrentRow(next_row)
        event.SetSelection(self.selection)
        self.ProcessEvent(event)
        self.OnSelectionChanged(next_row, self.selection)

        self.Refresh()

    def RowNumberByCoords(self, x, y):
        row = (y+LINH/2) / LINH - 1

        if row < 0 or row >= len(self.rows):
            return None
        else:
            return row

    def CommitByRow(self, row):
        return self.rows[row][0].commit

    def GotoCommit(self, commit_id):
        matching_commits = [c for c in self.commits if c.sha1.startswith(commit_id)]
        if len(matching_commits) == 0:
            return "Commit id '%s' cannot be found" % commit_id
        elif len(matching_commits) > 1:
            return "Given commit ID (%s) is ambiguous" % commit_id
        else:
            self.SelectRow(self.commits.index(matching_commits[0]))
            return None

    def SelectRow(self, row):
        self.selection = [row]
        
        # Emit selection event
        event = CommitListEvent(EVT_COMMITLIST_SELECT_type, self.GetId())
        event.SetCurrentRow(row)
        event.SetSelection(self.selection)
        self.ProcessEvent(event)
        self.OnSelectionChanged(row, self.selection)
        
        # Scroll to position
        start_col, start_row = self.GetViewStart()
        size = self.GetClientSize()
        height = size.GetHeight() / LINH
        
        if row < start_row or row > start_row+height-1:
            self.Scroll(start_col, max(row-2, 0))
        
        self.Refresh()

    # Virtual event handlers
    def OnSelectionChanged(self, row, selection):
        pass

    def OnRightButtonClicked(self, row, selection):
        pass

EVT_COMMITLIST_SELECT_type = wx.NewEventType()
EVT_COMMITLIST_SELECT = wx.PyEventBinder(EVT_COMMITLIST_SELECT_type, 1)

EVT_COMMITLIST_RIGHTCLICK_type = wx.NewEventType()
EVT_COMMITLIST_RIGHTCLICK = wx.PyEventBinder(EVT_COMMITLIST_RIGHTCLICK_type, 1)

class CommitListEvent(wx.PyCommandEvent):
    def __init__(self, eventType, id):
        wx.PyCommandEvent.__init__(self, eventType, id)
        self.selection = None
        self.currentRow = None
        self.coords = (None, None)

    def GetCurrentRow(self):
        return self.currentRow

    def SetCurrentRow(self, currentRow):
        self.currentRow = currentRow

    def GetSelection(self):
        return self.selection

    def SetSelection(self, selection):
        self.selection = selection

    def SetCoords(self, coords):
        self.coords = coords

    def GetCoords(self):
        return self.coords

NODE_NORMAL   = 0
NODE_BRANCH   = 1
NODE_MERGE    = 2
NODE_JUNCTION = 3

REF_BRANCH       = 0
REF_REMOTE       = 1
REF_TAG          = 2
REF_HEADBRANCH   = 3
REF_DETACHEDHEAD = 4
REF_MODULE       = 5
class GraphNode(object):
    def __init__(self, commit):
        self.commit = commit
        self.x = None
        self.y = None
        self.color = None

        self.parent_edges = []
        self.child_edges  = []
        self.references   = []

        if len(commit.parents) > 1 and len(commit.children) > 1:
            self.style = NODE_JUNCTION
        elif len(commit.parents) > 1:
            self.style = NODE_MERGE
        elif len(commit.children) > 1:
            self.style = NODE_BRANCH
        else:
            self.style = NODE_NORMAL

EDGE_DIRECT = 0
EDGE_BRANCH = 1
EDGE_MERGE  = 2
class GraphEdge(object):
    def __init__(self, src, dst):
        self.src = src
        self.dst = dst

        self.style = None
        self.color = None
        self.x = None
        self.color = None


########NEW FILE########
__FILENAME__ = Dialogs
import wx
import wx.lib.mixins.listctrl as listmixins
import git

from DiffViewer import DiffViewer
from IndexTab import MOD_DESCS
from util import *

class AutosizedListCtrl(wx.ListCtrl, listmixins.ListCtrlAutoWidthMixin):
    def __init__(self, parent, ID, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmixins.ListCtrlAutoWidthMixin.__init__(self)

class DiffDialog(wx.Dialog):
    def __init__(self, parent, id, title='', message=''):
        wx.Dialog.__init__(self, parent, id, size=(600,600), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.SetTitle(title)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        # Splitter
        self.splitter = wx.SplitterWindow(self, -1, style=wx.SP_LIVE_UPDATE)
        self.sizer.Add(self.splitter, True, wx.EXPAND, wx.ALL)

        self.topPanel = wx.Panel(self.splitter, -1)
        self.topSizer = wx.BoxSizer(wx.VERTICAL)
        self.topPanel.SetSizer(self.topSizer)

        self.bottomPanel = wx.Panel(self.splitter, -1)
        self.bottomSizer = wx.BoxSizer(wx.VERTICAL)
        self.bottomPanel.SetSizer(self.bottomSizer)

        # Message
        self.messageTxt = wx.StaticText(self.topPanel, -1, message)
        self.topSizer.Add(self.messageTxt, 0, wx.EXPAND | wx.ALL, 5)

        # List
        self.listCtrl = AutosizedListCtrl(self.topPanel, -1, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.listCtrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnListItemSelected)
        self.topSizer.Add(self.listCtrl, 1, wx.EXPAND | wx.ALL, 5)

        # DiffViewer
        self.diffViewer = DiffViewer(self.bottomPanel, -1)
        self.bottomSizer.Add(self.diffViewer, 1, wx.EXPAND | wx.ALL, 5)

        # Close button
        self.closeButton = wx.Button(self.bottomPanel, -1, 'Close')
        self.closeButton.Bind(wx.EVT_BUTTON, self.OnClose)
        self.bottomSizer.Add(self.closeButton, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        # Layout
        self.splitter.SetMinimumPaneSize(200)
        self.splitter.SplitHorizontally(self.topPanel, self.bottomPanel, 250)

    def SetMessage(self, message):
        self.messageTxt.SetLabel(message)

    def OnListItemSelected(self, e):
        pass

    def OnClose(self, e):
        self.EndModal(0)

class CommitListDialog(DiffDialog):
    def __init__(self, parent, id, repo, commits, title='', message=''):
        DiffDialog.__init__(self, parent, id, title, message)
        self.repo = repo
        self.commits = commits

        # Setup list control
        self.listCtrl.InsertColumn(0, "Author")
        self.listCtrl.InsertColumn(1, "Commit message")
        self.listCtrl.InsertColumn(2, "Date")

        self.listCtrl.SetColumnWidth(0, 150)
        self.listCtrl.SetColumnWidth(1, 300)
        self.listCtrl.SetColumnWidth(2, wx.LIST_AUTOSIZE)

        # Fill list control
        n = 0
        for commit in commits:
            self.listCtrl.InsertStringItem(n, commit.author_name)
            self.listCtrl.SetStringItem(n, 1, commit.short_msg)
            self.listCtrl.SetStringItem(n, 2, commit.author_date)
            n += 1

    def OnListItemSelected(self, e):
        rowid = e.GetIndex()
        commit = self.commits[rowid]

        commit_diff = self.repo.run_cmd(['show', commit.sha1])
        self.diffViewer.SetDiffText(commit_diff, commit_mode=True)

class UncommittedFilesDialog(DiffDialog):
    def __init__(self, parent, id, repo, title='', message=''):
        DiffDialog.__init__(self, parent, id, title, message)
        self.repo = repo

        # Get status
        self.status = repo.get_unified_status()
        self.files = self.status.keys()
        self.files.sort()

        # Setup list control
        self.listCtrl.InsertColumn(0, "Filename")
        self.listCtrl.InsertColumn(1, "Modification")

        self.listCtrl.SetColumnWidth(0, 500)
        self.listCtrl.SetColumnWidth(1, wx.LIST_AUTOSIZE)

        # Fill list control
        n = 0
        for file in self.files:
            self.listCtrl.InsertStringItem(n, file)
            self.listCtrl.SetStringItem(n, 1, MOD_DESCS[self.status[file]])
            n += 1

    def OnListItemSelected(self, e):
        rowid = e.GetIndex()
        file = self.files[rowid]

        if self.status[file] == git.FILE_UNTRACKED:
            commit_diff = git.diff_for_untracked_file(os.path.join(self.repo.dir, file))
        else:
            commit_diff = self.repo.run_cmd(['diff', 'HEAD', file])

        self.diffViewer.SetDiffText(commit_diff, commit_mode=False)


########NEW FILE########
__FILENAME__ = DiffViewer
import wx
import wx.stc
import platformspec
from util import *

STYLE_NORMAL  = 1
STYLE_COMMIT  = 2
STYLE_FILE    = 3
STYLE_HUNK    = 4
STYLE_ADD     = 5
STYLE_REMOVE  = 6

MARK_FILE = 1

STYLE_COLORS = [
    None,
    ('#000000', '#FFFFFF', wx.FONTWEIGHT_NORMAL), # STYLE_NORMAL
    ('#000000', '#FFFFFF', wx.FONTWEIGHT_BOLD),   # STYLE_COMMIT
    ('#000000', '#AAAAAA', wx.FONTWEIGHT_BOLD),   # STYLE_FILE
    ('#0000AA', '#FFFFFF', wx.FONTWEIGHT_NORMAL), # STYLE_HUNK
    ('#008800', '#FFFFFF', wx.FONTWEIGHT_NORMAL), # STYLE_ADD
    ('#AA0000', '#FFFFFF', wx.FONTWEIGHT_NORMAL)  # STYLE_REMOVE
]

class DiffViewer(wx.Panel):
    def __init__(self, parent, id):
        wx.Panel.__init__(self, parent, id)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        # Create text control
        self.textCtrl = wx.stc.StyledTextCtrl(self, -1)
        self.sizer.Add(self.textCtrl, True, wx.EXPAND)

        # Create markers
        self.textCtrl.MarkerDefine(MARK_FILE,
            wx.stc.STC_MARK_BACKGROUND,
            wx.Colour(0,0,0,255),
            wx.Colour(192,192,192,255)
        )

        # Create text styles
        for style in xrange(1, len(STYLE_COLORS)):
            fg, bg, weight = STYLE_COLORS[style]
            font = platformspec.Font(10, wx.FONTFAMILY_TELETYPE)
            
            self.textCtrl.StyleSetFont(style, font)
            self.textCtrl.StyleSetForeground(style, fg)
            self.textCtrl.StyleSetBackground(style, bg)

    def Clear(self):
        self.textCtrl.SetReadOnly(False)
        self.textCtrl.SetText('')
        self.textCtrl.SetReadOnly(True)

    def SetDiffText(self, text, commit_mode=False):
        self.Clear()
        self.textCtrl.SetReadOnly(False)

        # Setup commit mode (when the text comes from the
        # output of git show, not git diff)
        if commit_mode:
            in_commit_header = True
            in_commit_msg = False
        else:
            in_commit_header = False
            in_commit_msg = False

        in_hunk = False
        style = STYLE_NORMAL
        pos = 0
        lineno = 0
        for line in text.split('\n'):
            # Determine line style
            if in_commit_header:
                if line == '':
                    in_commit_header = False
                    in_commit_msg = True
                style = STYLE_COMMIT
            elif in_commit_msg:
                if line == '':
                    in_commit_msg = False
                style = STYLE_COMMIT
            elif in_hunk:
                if line.startswith('+'):
                    style = STYLE_ADD
                elif line.startswith('-'):
                    style = STYLE_REMOVE
                elif line.startswith('@'):
                    style = STYLE_HUNK
                elif line.startswith(' '):
                    style = STYLE_NORMAL
                else:
                    in_hunk = False
                    style = STYLE_FILE
            else:
                if line.startswith('@'):
                    style = STYLE_HUNK
                    in_hunk = True
                else:
                    style = STYLE_FILE

            # Add line
            self.textCtrl.AddText(safe_unicode(line) + '\n')
            self.textCtrl.StartStyling(pos, 0xff)
            self.textCtrl.SetStyling(len(line), style)
            pos += len(line) + 1

            if style == STYLE_FILE and len(line) > 0:
                self.textCtrl.MarkerAdd(lineno, MARK_FILE)

            lineno += 1

        self.textCtrl.SetReadOnly(True)
            

########NEW FILE########
__FILENAME__ = FetchDialogs
import wx
from git import *

class FetchSetupDialog(wx.Dialog):
    def __init__(self, parent, id, repo):
        wx.Dialog.__init__(self, parent)
        self.repo = repo

        self.SetTitle('Fetch objects from remote repository')
        self.Bind(wx.EVT_CLOSE, self.OnCancel)

        # Layout
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        remoteSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(remoteSizer, 0, wx.EXPAND | wx.ALL, 5)

        # Remote selector
        remoteChooserText = wx.StaticText(self, -1, 'Remote repository: ')
        remoteSizer.Add(remoteChooserText, 0, wx.ALIGN_CENTRE_VERTICAL, wx.RIGHT, 5)

        self.remoteChoices = [name for name,url in self.repo.remotes.iteritems()]
        self.remoteChoices.sort()

        self.remoteChooser = wx.Choice(self, -1, choices=self.remoteChoices)
        topPadding = 4 if sys.platform == 'darwin' else 0
        remoteSizer.Add(self.remoteChooser, 0, wx.EXPAND | wx.ALIGN_CENTRE_VERTICAL | wx.TOP, topPadding)
        self.remoteChooser.Select(0)
        self.remoteChooser.Bind(wx.EVT_CHOICE, self.OnRemoteChosen)

        # Remote URL
        self.remoteURLText = wx.StaticText(self, -1, '', style=wx.ALIGN_LEFT)
        self.sizer.Add(self.remoteURLText, 0, wx.ALL, 5)

        # Include submodules
        if self.repo.submodules:
            self.submoduleChk = wx.CheckBox(self, -1, label='Also fetch submodule commits')
            self.submoduleChk.SetValue(True)
            self.submoduleChk.Bind(wx.EVT_CHECKBOX, self.OnSubmoduleCheck)
            self.sizer.Add(self.submoduleChk, 0, wx.ALL, 5)
            self.includeSubmodules = True
        else:
            self.includeSubmodules = False

        # Fetch tags
        self.tagsChk = wx.CheckBox(self, -1, label='Fetch remote tags')
        self.tagsChk.Bind(wx.EVT_CHECKBOX, self.OnTagsCheck)
        self.sizer.Add(self.tagsChk, 0, wx.ALL, 5)
        self.fetchTags = False

        self.OnRemoteChosen(None)

        # Buttons
        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(buttonSizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        okButton = wx.Button(self, -1, 'OK')
        okButton.Bind(wx.EVT_BUTTON, self.OnOk)
        buttonSizer.Add(okButton, 0, wx.RIGHT | wx.BOTTOM, 5)

        cancelButton = wx.Button(self, -1, 'Cancel')
        cancelButton.Bind(wx.EVT_BUTTON, self.OnCancel)
        buttonSizer.Add(cancelButton, 0, wx.LEFT | wx.BOTTOM, 5)

        self.Fit()

    def OnRemoteChosen(self, e):
        remoteIndex = self.remoteChooser.GetSelection()
        self.selectedRemote = self.remoteChoices[remoteIndex]

        # Update labels
        self.remoteURLText.SetLabel('URL: %s' % self.repo.remotes[self.selectedRemote])

        if self.repo.submodules:
            self.submoduleChk.SetLabel('Also fetch submodule commits from remote "%s"' % self.selectedRemote)

        # Fetch tags by default if the remote name is 'origin'
        self.fetchTags = (self.selectedRemote == 'origin')
        self.tagsChk.SetValue(self.fetchTags)

        # Update window size
        textSize = self.remoteURLText.GetSize()
        winSize = self.GetClientSize()
        self.SetClientSize( (max(winSize[0],textSize[0]+20), winSize[1]) )
        self.Layout()

    def OnSubmoduleCheck(self, e):
        self.includeSubmodules = self.submoduleChk.GetValue()

    def OnTagsCheck(self, e):
        self.fetchTags = self.tagsChk.GetValue()

    def OnOk(self, e):
        self.EndModal(1)

    def OnCancel(self, e):
        self.EndModal(0)

class FetchProgressDialog(wx.Dialog):
    def __init__(self, parent, id, repo, remote, includeSubmodules, fetchTags):
        wx.Dialog.__init__(self, parent, id)
        self.repo = repo
        self.remote = remote
        self.includeSubmodules = includeSubmodules
        self.fetchTags = fetchTags

        # Repositories
        self.repos = [ repo ]
        self.repoIndex = 0
        if includeSubmodules:
            self.repos += [ m for m in repo.submodules if remote in m.remotes ]

        # Layout
        self.SetTitle('Fetching from remote %s...' % remote)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        # Submodule progress
        if len(self.repos) > 1:
            self.submoduleText = wx.StaticText(self, -1, '')
            self.sizer.Add(self.submoduleText, 0, wx.ALL, 10)

            self.submoduleProgress = wx.Gauge(self, -1)
            self.submoduleProgress.SetRange(len(self.repos)-1)
            self.sizer.Add(self.submoduleProgress, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        else:
            self.submoduleText = None

        # Progress text
        self.progressText = wx.StaticText(self, -1, 'Connecting to remote repository...')
        self.sizer.Add(self.progressText, 0, wx.ALL, 10)

        # Progress bar
        self.progressBar = wx.Gauge(self, -1)
        self.progressBar.SetRange(100)
        self.sizer.Add(self.progressBar, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Cancel button
        self.cancelButton = wx.Button(self, -1, 'Cancel')
        self.cancelButton.Bind(wx.EVT_BUTTON, self.OnCancel)
        self.sizer.Add(self.cancelButton, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        self.Bind(wx.EVT_CLOSE, self.OnCancel)

        # Set dialog size
        self.Fit()
        w,h = self.GetClientSize()
        if w < 350:
            self.SetClientSize((350, h))
            self.Layout()

    def ShowModal(self):
        self.StartRepo()
        return wx.Dialog.ShowModal(self)

    def StartRepo(self):
        repo = self.repos[self.repoIndex]

        if self.submoduleText:
            self.submoduleText.SetLabel('Fetching commits for %s...' % repo.name)
            self.submoduleProgress.SetValue(self.repoIndex)

            # Resize window if necessary
            tw,th = self.submoduleText.GetClientSize()
            w,h = self.GetClientSize()
            if w < tw+20:
                self.SetClientSize((tw+20, h))
                self.Layout()

        self.progressText.SetLabel('Connecting to remote repository...')
        self.progressBar.Pulse()
        self.fetchThread = repo.fetch_bg(self.remote, self.ProgressCallback, self.fetchTags)
        self.repoIndex += 1

    def ProgressCallback(self, event, param):
        if event == TRANSFER_COUNTING:
            wx.CallAfter(self.progressText.SetLabel, "Counting objects: %d" % param)
        elif event == TRANSFER_COMPRESSING:
            wx.CallAfter(self.progressText.SetLabel, "Compressing objects...")
            wx.CallAfter(self.progressBar.SetValue, param)
        elif event == TRANSFER_RECEIVING:
            wx.CallAfter(self.progressText.SetLabel, "Receiving objects...")
            wx.CallAfter(self.progressBar.SetValue, param)
        elif event == TRANSFER_RESOLVING:
            wx.CallAfter(self.progressText.SetLabel, "Resolving deltas...")
            wx.CallAfter(self.progressBar.SetValue, param)
        elif event == TRANSFER_ENDED:
            wx.CallAfter(self.OnFetchEnded, param)

    def OnFetchEnded(self, param):
        self.fetchThread.join()
        self.fetchThread = None

        if type(param) in [str, unicode]:
            # Error
            wx.MessageBox(safe_unicode(param), 'Error', style=wx.OK|wx.ICON_ERROR)
            self.EndModal(0)
        else:
            # Success
            if len(self.repos) > self.repoIndex:
                self.StartRepo()
            else:
                self.EndModal(1)

    def OnCancel(self, e):
        if self.fetchThread:
            self.fetchThread.abort()
            self.fetchThread.join()

        self.EndModal(0)


########NEW FILE########
__FILENAME__ = git
import os
import os.path
import sys
import subprocess
import re
import tempfile
import threading
from util import *

FILE_ADDED       = 'A'
FILE_MODIFIED    = 'M'
FILE_DELETED     = 'D'
FILE_COPIED      = 'C'
FILE_RENAMED     = 'R'
FILE_UNMERGED    = 'U'
FILE_TYPECHANGED = 'T'
FILE_UNTRACKED   = 'N'
FILE_BROKEN      = 'B'
FILE_UNKNOWN     = 'X'

MERGE_TOOLS = {
    'opendiff': (
        ['/usr/bin/opendiff'],
        ['{LOCAL}', '{REMOTE}', '-merge', '{MERGED}']
    ),
    'diffmerge.app': (
        ['/Applications/DiffMerge.app/Contents/MacOS/DiffMerge'],
        ['--nosplash', '-t1={FILENAME}.LOCAL', '-t2={FILENAME}.MERGED', '-t3={FILENAME}.REMOTE', '{LOCAL}', '{MERGED}', '{REMOTE}']
    ),
    'diffmerge.cmdline': (
        ['{PATH}/diffmerge', '{PATH}/diffmerge.sh'],
        ['--nosplash', '-t1=LOCAL', '-t2=MERGED', '-t3=REMOTE', '{LOCAL}', '{MERGED}', '{REMOTE}']
    ),
    'meld': (
        ['{PATH}/meld'],
        ['{LOCAL}', '{MERGED}', '{REMOTE}']
    ),
    'kdiff3': (
        ['{PATH}/kdiff3'],
        ['{LOCAL}', '{MERGED}', '{REMOTE}', '-o', '{MERGED}', '--L1', '{FILENAME}.LOCAL', '--L2', '{FILENAME}.MERGED', '--L3', '{FILENAME}.REMOTE']
    ),
    'winmerge': (
        [r'C:\Program Files\WinMerge\WinMergeU.exe'],
        ['{MERGED}'] # It does not support 3-way merge yet...
    ),
    'tortoisemerge': (
        [r'C:\Program Files\TortoiseGit\bin\TortoiseMerge.exe'],
        ['{MERGED}', '{LOCAL}', '{REMOTE}']
    ),
}

_git = None
commit_pool = {}

class GitError(RuntimeError): pass

def git_binary():
    global _git

    if _git:
        return _git

    # Search for git binary
    if os.name == 'posix':
        locations = ['{PATH}/git', '/opt/local/bin/git', '/usr/local/git/bin']
    elif sys.platform == 'win32':
        locations = (r'{PATH}\git.exe', r'C:\Program Files\Git\bin\git.exe')
    else:
        locations = []

    for _git in find_binary(locations):
        return _git

    _git = None
    raise GitError, "git executable not found"

_mergetool = None
def detect_mergetool():
    global _mergetool

    if _mergetool:
        return _mergetool

    # Select tools
    if sys.platform == 'darwin':
        # Mac OS X
        tools = ['diffmerge.app', 'diffmerge.cmdline', 'opendiff', 'meld']
    elif os.name == 'posix':
        # Other Unix
        tools = ['diffmerge.cmdline', 'meld', 'kdiff3']
    elif sys.platform == 'win32':
        # Windows
        tools = ['tortoisemerge', 'winmerge']
    else:
        raise GitError, "Cannot detect any merge tool"

    # Detect binaries
    for tool in tools:
        locations, args = MERGE_TOOLS[tool]
        for location in find_binary(locations):
            _mergetool = (location, args)
            return _mergetool

    # Return error if no tool was found
    raise GitError, "Cannot detect any merge tool"

def run_cmd(dir, args, with_retcode=False, with_stderr=False, raise_error=False, input=None, env={}, run_bg=False, setup_askpass=False):
    # Check args
    if type(args) in [str, unicode]:
        args = [args]
    args = [str(a) for a in args]

    # Check directory
    if not os.path.isdir(dir):
        raise GitError, 'Directory not exists: ' + dir

    try:
        os.chdir(dir)
    except OSError, msg:
        raise GitError, msg

    # Run command
    if type(args) != list:
        args = [args]

    # Setup environment
    git_env = dict(os.environ)
    if setup_askpass and 'SSH_ASKPASS' not in git_env:
        git_env['SSH_ASKPASS'] = '%s-askpass' % os.path.realpath(os.path.abspath(sys.argv[0]))

    git_env.update(env)
    
    preexec_fn = os.setsid if setup_askpass else None

    p = Popen([git_binary()] + args, stdout=subprocess.PIPE,
              stderr=subprocess.PIPE, stdin=subprocess.PIPE,
              env=git_env, shell=False, preexec_fn=preexec_fn)
    if run_bg:
        return p

    if input == None:
        stdout,stderr = p.communicate('')
    else:
        stdout,stderr = p.communicate(utf8_str(input))
    
    # Return command output in a form given by arguments
    ret = []

    if p.returncode != 0 and raise_error:
        raise GitError, 'git returned with the following error:\n%s' % stderr

    if with_retcode:
        ret.append(p.returncode)

    ret.append(stdout)

    if with_stderr:
        ret.append(stderr)

    if len(ret) == 1:
        return ret[0]
    else:
        return tuple(ret)

class Repository(object):
    def __init__(self, repodir, name='Main module', parent=None):
        self.name = name
        self.parent = parent

        # Search for .git directory in repodir ancestors
        repodir = os.path.abspath(repodir)
        try:
            if parent:
                if not os.path.isdir(os.path.join(repodir, '.git')):
                    raise GitError, "Not a git repository: %s" % repodir
            else:
                while not os.path.isdir(os.path.join(repodir, '.git')):
                    new_repodir = os.path.abspath(os.path.join(repodir, '..'))
                    if new_repodir == repodir or (parent and new_repodir == parent.dir):
                        raise GitError, "Directory is not a git repository"
                    else:
                        repodir = new_repodir
        except OSError:
            raise GitError, "Directory is not a git repository or it is not readable"
            
        self.dir = repodir

        # Remotes
        self.config = ConfigFile(os.path.join(self.dir, '.git', 'config'))
        self.url = self.config.get_option('remote', 'origin', 'url')

        self.remotes = {}
        for remote, opts in self.config.sections_for_type('remote'):
            if 'url' in opts:
                self.remotes[remote] = opts['url']

        # Run a git status to see whether this is really a git repository
        retcode,output = self.run_cmd(['status'], with_retcode=True)
        if retcode not in [0,1]:
            raise GitError, "Directory is not a git repository"

        # Load refs
        self.load_refs()

        # Get submodule info
        self.submodules = self.get_submodules()
        self.all_modules = [self] + self.submodules

    def load_refs(self):
        self.refs = {}
        self.branches = {}
        self.remote_branches = {}
        self.tags = {}

        # HEAD, current branch
        self.head = self.run_cmd(['rev-parse', 'HEAD']).strip()
        self.current_branch = None
        try:
            f = open(os.path.join(self.dir, '.git', 'HEAD'))
            head = f.read().strip()
            f.close()

            if head.startswith('ref: refs/heads/'):
                self.current_branch = head[16:]
        except OSError:
            pass

        # Main module references
        if self.parent:
            self.main_ref = self.parent.get_submodule_version(self.name, 'HEAD')
            if os.path.exists(os.path.join(self.parent.dir, '.git', 'MERGE_HEAD')):
                self.main_merge_ref = self.parent.get_submodule_version(self.name, 'MERGE_HEAD')
            else:
                self.main_merge_ref = None
        else:
            self.main_ref = None
            self.main_merge_ref = None

        # References
        for line in self.run_cmd(['show-ref']).split('\n'):
            commit_id, _, refname = line.partition(' ')
            self.refs[refname] = commit_id

            if refname.startswith('refs/heads/'):
                branchname = refname[11:]
                self.branches[branchname] = commit_id
            elif refname.startswith('refs/remotes/'):
                branchname = refname[13:]
                self.remote_branches[branchname] = commit_id
            elif refname.startswith('refs/tags/'):
                # Load the referenced commit for tags
                tagname = refname[10:]
                try:
                    self.tags[tagname] = self.run_cmd(['rev-parse', '%s^{commit}' % refname], raise_error=True).strip()
                except GitError:
                    pass

        # Inverse reference hashes
        self.refs_by_sha1 = invert_hash(self.refs)
        self.branches_by_sha1 = invert_hash(self.branches)
        self.remote_branches_by_sha1 = invert_hash(self.remote_branches)
        self.tags_by_sha1 = invert_hash(self.tags)

    def run_cmd(self, args, **opts):
        return run_cmd(self.dir, args, **opts)

    def get_submodules(self):
        # Check existence of .gitmodules
        gitmodules_path = os.path.join(self.dir, '.gitmodules')
        if not os.path.isfile(gitmodules_path):
            return []

        # Parse .gitmodules file
        repos = []
        submodule_config = ConfigFile(gitmodules_path)
        for name,opts in submodule_config.sections_for_type('submodule'):
            if 'path' in opts:
                repo_path = os.path.join(self.dir, opts['path'])
                repos.append(Repository(repo_path, name=opts['path'], parent=self))

        return repos

    def get_submodule_version(self, submodule_name, main_version):
        dir = os.path.dirname(submodule_name)
        name = os.path.basename(submodule_name)
        output = self.run_cmd(['ls-tree', '-z', '%s:%s' % (main_version, dir)])
        for line in output.split('\x00'):
            if not line.strip(): continue

            meta, filename = line.split('\t')
            if filename == name:
                mode, filetype, sha1 = meta.split(' ')
                if filetype == 'commit':
                    return sha1

        return None

    def get_log(self, args=[]):
        log = self.run_cmd(['log', '-z', '--date=relative', '--pretty=format:%H%n%h%n%P%n%T%n%an%n%ae%n%ad%n%s%n%b']+args)
        
        if len(log) == 0:
            return []

        commit_texts = log.split('\x00')
        commit_texts.reverse()

        commits = []
        for text in commit_texts:
            c = Commit(self)
            c.parse_gitlog_output(text)
            commit_pool[c.sha1] = c
            commits.append(c)

        commits.reverse()
        return commits

    def commit(self, author_name, author_email, msg, amend=False):
        if amend:
            # Get details of current HEAD
            is_merge_resolve = False

            output = self.run_cmd(['log', '-1', '--pretty=format:%P%n%an%n%ae%n%aD'])
            if not output.strip():
                raise GitError, "Cannot amend in an empty repository!"

            parents, author_name, author_email, author_date = output.split('\n')
            parents = parents.split(' ')
        else:
            author_date = None # Use current date

            # Get HEAD sha1 id
            if self.head == 'HEAD':
                parents = []
            else:
                head = self.run_cmd(['rev-parse', 'HEAD']).strip()
                parents = [head]

            # Get merge head if exists
            is_merge_resolve = False
            try:
                merge_head_filename = os.path.join(self.dir, '.git', 'MERGE_HEAD')
                if os.path.isfile(merge_head_filename):
                    f = open(merge_head_filename)
                    p = f.read().strip()
                    f.close()
                    parents.append(p)
                    is_merge_resolve = True
            except OSError:
                raise GitError, "Cannot open MERGE_HEAD file"

        # Write tree
        tree = self.run_cmd(['write-tree'], raise_error=True).strip()

        # Write commit
        parent_args = []
        for parent in parents:
            parent_args += ['-p', parent]

        env = {}
        if author_name: env['GIT_AUTHOR_NAME'] = author_name
        if author_email: env['GIT_AUTHOR_EMAIL'] = author_email
        if author_date: env['GIT_AUTHOR_DATE'] = author_date

        commit = self.run_cmd(
            ['commit-tree', tree] + parent_args,
            raise_error=True,
            input=msg,
            env=env
        ).strip()

        # Update reference
        self.run_cmd(['update-ref', 'HEAD', commit], raise_error=True)

        # Remove MERGE_HEAD
        if is_merge_resolve:
            try:
                os.unlink(os.path.join(self.dir, '.git', 'MERGE_HEAD'))
                os.unlink(os.path.join(self.dir, '.git', 'MERGE_MODE'))
                os.unlink(os.path.join(self.dir, '.git', 'MERGE_MSG'))
                os.unlink(os.path.join(self.dir, '.git', 'ORIG_HEAD'))
            except OSError:
                pass

    def get_status(self):
        unstaged_changes = {}
        staged_changes = {}

        # Unstaged changes
        changes = self.run_cmd(['diff', '--name-status', '-z']).split('\x00')
        for i in xrange(len(changes)/2):
            status, filename = changes[2*i], changes[2*i+1]
            if filename not in unstaged_changes or status == FILE_UNMERGED:
                unstaged_changes[filename] = status

        # Untracked files
        for filename in self.run_cmd(['ls-files', '--others', '--exclude-standard', '-z']).split('\x00'):
            if filename and filename not in unstaged_changes:
                unstaged_changes[filename] = FILE_UNTRACKED

        # Staged changes
        if self.head == 'HEAD':
            # Initial commit
            for filename in self.run_cmd(['ls-files', '--cached', '-z']).split('\x00'):
                if filename:
                    staged_changes[filename] = FILE_ADDED
        else:
            changes = self.run_cmd(['diff', '--cached', '--name-status', '-z']).split('\x00')
            for i in xrange(len(changes)/2):
                status, filename = changes[2*i], changes[2*i+1]
                if status != FILE_UNMERGED or filename not in unstaged_changes:
                    staged_changes[filename] = status

        return unstaged_changes, staged_changes

    def get_unified_status(self):
        unified_changes = {}

        # Staged & unstaged changes
        changes = self.run_cmd(['diff', 'HEAD', '--name-status', '-z']).split('\x00')
        for i in xrange(len(changes)/2):
            status, filename = changes[2*i], changes[2*i+1]
            if filename not in unified_changes or status == FILE_UNMERGED:
                unified_changes[filename] = status

        # Untracked files
        for filename in self.run_cmd(['ls-files', '--others', '--exclude-standard', '-z']).split('\x00'):
            if filename and filename not in unified_changes:
                unified_changes[filename] = FILE_UNTRACKED

        return unified_changes

    def merge_file(self, filename):
        # Store file versions in temporary files
        fd, local_file = tempfile.mkstemp(prefix=os.path.basename(filename) + '.LOCAL.')
        os.write(fd, self.run_cmd(['show', ':2:%s' % filename], raise_error=True))
        os.close(fd)

        fd, remote_file = tempfile.mkstemp(prefix=os.path.basename(filename) + '.REMOTE.')
        os.write(fd, self.run_cmd(['show', ':3:%s' % filename], raise_error=True))
        os.close(fd)
        
        # Run mergetool
        mergetool, args = detect_mergetool()
        args = list(args)

        for i in xrange(len(args)):
            args[i] = args[i].replace('{FILENAME}', os.path.basename(filename))
            args[i] = args[i].replace('{LOCAL}', local_file)
            args[i] = args[i].replace('{REMOTE}', remote_file)
            args[i] = args[i].replace('{MERGED}', os.path.join(self.dir, filename))

        s = Popen([mergetool] + args, shell=False)

    def get_lost_commits(self, refname, moving_to=None):
        # Note: refname must be a full reference name (e.g. refs/heads/master)
        # or HEAD (if head is detached).
        # moving_to must be a SHA1 commit identifier
        if refname == 'HEAD':
            commit_id = self.head
        else:
            commit_id = self.refs[refname]
        commit = commit_pool[commit_id]

        # If commit is not moving, it won't be lost :)
        if commit_id == moving_to:
            return []

        # If a commit has another reference, it won't be lost :)
        head_refnum = len(self.refs_by_sha1.get(commit_id, []))
        if (refname == 'HEAD' and head_refnum > 0) or head_refnum > 1:
            return []

        # If commit has descendants, it won't be lost: at least one of its
        # descendants has another reference
        if commit.children:
            return []

        # If commit has parents, traverse the commit graph into this direction.
        # Mark every commit as lost commit until:
        #   (1) the end of the graph is found
        #   (2) a reference is found
        #   (3) the moving_to destination is found
        #   (4) a commit is found that has more than one children.
        #       (it must have a descendant that has a reference)
        lost_commits = []
        search_pos = [commit]

        while search_pos:
            next_search_pos = []

            for c in search_pos:
                for p in c.parents:
                    if p.sha1 not in self.refs_by_sha1 and p.sha1 != moving_to \
                        and len(p.children) == 1:
                        next_search_pos.append(p)

            lost_commits += search_pos
            search_pos = next_search_pos

        return lost_commits

    def update_head(self, content):
        try:
            f = open(os.path.join(self.dir, '.git', 'HEAD'), 'w')
            f.write(content)
            f.close()
        except OSError:
            raise GitError, "Write error:\nCannot write into .git/HEAD"

    def fetch_bg(self, remote, callbackFunc, fetch_tags=False):
        url = self.remotes[remote]
        t = FetchThread(self, remote, callbackFunc, fetch_tags)
        t.start()

        return t

    def push_bg(self, remote, commit, remoteBranch, forcePush, callbackFunc):
        t = PushThread(self, remote, commit, remoteBranch, forcePush, callbackFunc)
        t.start()

        return t

class Commit(object):
    def __init__(self, repo):
        self.repo = repo

        self.sha1 = None
        self.abbrev = None

        self.parents = None
        self.children = None
        self.tree = None

        self.author_name = None
        self.author_email = None
        self.author_date = None

        self.short_msg = None
        self.full_msg = None

        self.remote_branches = None
        self.branches = None
        self.tags = None

    def parse_gitlog_output(self, text):
        lines = text.split('\n')

        (self.sha1, self.abbrev, parents, self.tree,
         self.author_name, self.author_email, self.author_date,
         self.short_msg) = lines[0:8]

        if parents:
            parent_ids = parents.split(' ')
            self.parents = [commit_pool[p] for p in parent_ids]
            for parent in self.parents:
                parent.children.append(self)
        else:
            self.parents = []

        self.children = []

        self.full_msg = '\n'.join(lines[8:])


class ConfigFile(object):
    def __init__(self, filename):
        self.sections = []

        # Patterns
        p_rootsect = re.compile(r'\[([^\]\s]+)\]')
        p_sect     = re.compile(r'\[([^\]"\s]+)\s+"([^"]+)"\]')
        p_option   = re.compile(r'(\w+)\s*=\s*(.*)')

        # Parse file
        section = None
        section_type = None
        options = {}

        f = open(filename)
        for line in f:
            line = line.strip()

            if len(line) == 0 or line.startswith('#'):
                continue

            # Parse sections
            m_rootsect = p_rootsect.match(line)
            m_sect     = p_sect.match(line)

            if (m_rootsect or m_sect) and section:
                self.sections.append( (section_type, section, options) )
            if m_rootsect:
                section_type = None
                section = m_rootsect.group(1)
                options = {}
            elif m_sect:
                section_type = m_sect.group(1)
                section = m_sect.group(2)
                options = {}
                
            # Parse options
            m_option = p_option.match(line)
            if section and m_option:
                options[m_option.group(1)] = m_option.group(2)

        if section:
            self.sections.append( (section_type, section, options) )
        f.close()

    def has_section(self, sect_type, sect_name):
        m = [ s for s in self.sections if s[0]==sect_type and s[1] == sect_name ]
        return len(m) > 0

    def sections_for_type(self, sect_type):
        return [ (s[1],s[2]) for s in self.sections if s[0]==sect_type ]

    def options_for_section(self, sect_type, sect_name):
        m = [ s[2] for s in self.sections if s[0]==sect_type and s[1] == sect_name ]
        if m:
            return m[0]
        else:
            return None

    def get_option(self, sect_type, sect_name, option):
        opts = self.options_for_section(sect_type, sect_name)
        if opts:
            return opts.get(option)
        else:
            return None

TRANSFER_COUNTING      = 0
TRANSFER_COMPRESSING   = 1
TRANSFER_RECEIVING     = 2
TRANSFER_WRITING       = 3
TRANSFER_RESOLVING     = 4
TRANSFER_ENDED         = 5
class ObjectTransferThread(threading.Thread):
    def __init__(self, repo, callback_func):
        threading.Thread.__init__(self)
        
        # Parameters
        self.repo = repo
        self.callback_func = callback_func

        # Regular expressions for progress indicator
        self.counting_expr      = re.compile(r'.*Counting objects:\s*([0-9]+)')
        self.compressing_expr   = re.compile(r'.*Compressing objects:\s*([0-9]+)%')
        self.receiving_expr     = re.compile(r'.*Receiving objects:\s*([0-9]+)%')
        self.writing_expr       = re.compile(r'.*Writing objects:\s*([0-9]+)%')
        self.resolving_expr     = re.compile(r'.*Resolving deltas:\s*([0-9]+)%')

        self.progress_exprs = (
            (self.counting_expr, TRANSFER_COUNTING),
            (self.compressing_expr, TRANSFER_COMPRESSING),
            (self.receiving_expr, TRANSFER_RECEIVING),
            (self.writing_expr, TRANSFER_WRITING),
            (self.resolving_expr, TRANSFER_RESOLVING)
        )

    def run(self, cmd):
        # Initial state
        self.error_msg = 'Unknown error occured'
        self.aborted = False

        # Run git
        self.process = self.repo.run_cmd(cmd, run_bg=True, setup_askpass=True)
        self.process.stdin.close()

        # Read stdout from a different thread (select.select() does not work
        # properly on Windows)
        stdout_thread = threading.Thread(target=self.read_stdout, args=[self.process.stdout], kwargs={})
        stdout_thread.start()

        # Read lines
        line = ''
        c = self.process.stderr.read(1)
        while c:
            if c in ['\n', '\r']:
                self.parse_line(line)
                line = ''
            else:
                line += c

            c = self.process.stderr.read(1)

        self.process.wait()
        stdout_thread.join()

        # Remaining line
        if line:
            self.parse_line(line)

        # Report end of operation
        if self.aborted:
            return
        elif self.process.returncode == 0:
            result = self.transfer_ended()
            self.callback_func(TRANSFER_ENDED, result)
        else:
            self.callback_func(TRANSFER_ENDED, self.error_msg)

    def parse_line(self, line):
        # Progress indicators
        for reg, event in self.progress_exprs:
            m = reg.match(line)
            if m:
                self.callback_func(event, int(m.group(1)))

        # Fatal error
        if line.startswith('fatal:'):
            self.error_msg = line

    def read_stdout(self, stdout):
        lines = stdout.read().split('\n')
        for line in lines:
            self.parse_line(line)

    def abort(self):
        self.aborted = True
        try:
            self.process.kill()
        except:
            pass

class FetchThread(ObjectTransferThread):
    def __init__(self, repo, remote, callback_func, fetch_tags=False):
        ObjectTransferThread.__init__(self, repo, callback_func)

        # Parameters
        self.remote = remote
        self.fetch_tags = fetch_tags

        # Regular expressions for remote refs
        self.branches = {}
        self.tags = {}
        self.branch_expr    = re.compile(r'([0-9a-f]{40}) refs\/heads\/([a-zA-Z0-9_.\-]+)')
        self.tag_expr       = re.compile(r'([0-9a-f]{40}) refs\/tags\/([a-zA-Z0-9_.\-]+)')

        self.ref_exprs = (
            (self.branch_expr, self.branches),
            (self.tag_expr, self.tags)
        )

    def run(self):
        ObjectTransferThread.run(self, ['fetch-pack', '-v', '--all', self.repo.remotes[self.remote]])
    
    def transfer_ended(self):
        # Update remote branches
        for branch, sha1 in self.branches.iteritems():
            self.repo.run_cmd(['update-ref', 'refs/remotes/%s/%s' % (self.remote, branch), sha1])

        # Update tags
        if self.fetch_tags:
            for tag, sha1 in self.tags.iteritems():
                self.repo.run_cmd(['update-ref', 'refs/tags/%s' % tag, sha1])
        
        return (self.branches, self.tags)

    def parse_line(self, line):
        ObjectTransferThread.parse_line(self, line)

        # Remote refs
        for reg, refs in self.ref_exprs:
            m = reg.match(line)
            if m:
                refs[m.group(2)] = m.group(1)

class PushThread(ObjectTransferThread):
    def __init__(self, repo, remote, commit, remote_branch, force_push, callback_func):
        ObjectTransferThread.__init__(self, repo, callback_func)

        # Parameters
        self.remote = remote
        self.commit = commit
        self.remote_branch = remote_branch
        self.force_push = force_push

    def run(self):
        if self.force_push:
            push_cmd = ['push', '-f']
        else:
            push_cmd = ['push']

        cmd = push_cmd + [self.remote, '%s:refs/heads/%s' % (self.commit.sha1, self.remote_branch)]
        ObjectTransferThread.run(self, cmd)

    def parse_line(self, line):
        ObjectTransferThread.parse_line(self, line)

        if line.startswith(' ! [rejected]'):
            self.error_msg = 'The pushed commit is non-fast forward.'

    def transfer_ended(self):
        return None

# Utility functions
def diff_for_untracked_file(filename):
    # Start "diff" text
    diff_text = 'New file: %s\n' % filename

    # Detect whether file is binary
    if is_binary_file(filename):
        diff_text += "@@ File is binary.\n\n"
    else:
        # Text file => show lines
        newfile_text = ''
        try:
            f = open(filename, 'r')
            lines = f.readlines()
            f.close()

            newfile_text += '@@ -1,0 +1,%d @@\n' % len(lines)

            for line in lines:
                newfile_text += '+ ' + line

            diff_text += newfile_text
        except OSError:
            diff_text += '@@ Error: Cannot open file\n\n'

    return diff_text


########NEW FILE########
__FILENAME__ = HiddenWindow
import wx
from MainWindow import *
from wxutil import *
from AboutDialog import ShowAboutDialog

class HiddenWindow(object):
    def __init__(self):
        super(HiddenWindow, self).__init__()
        self.frame = LoadFrame(None, 'HiddenWindow')
        
        SetupEvents(self.frame, [
            (None, wx.EVT_CLOSE, self.OnWindowClosed),
            ('quitMenuItem', wx.EVT_MENU, self.OnExit),
            ('openMenuItem', wx.EVT_MENU, self.OnOpenRepository),
            ('newWindowMenuItem', wx.EVT_MENU, self.OnNewWindow),
            ('aboutMenuItem', wx.EVT_MENU, self.OnAbout),
        ])
    
    def ShowMenu(self):
        self.frame.SetPosition((-10000,-10000))
        self.frame.Show()
        self.frame.Hide()

    def OnWindowClosed(self, e):
        # Do nothing
        pass

    def OnNewWindow(self, e):
        win = MainWindow(None)
        win.Show(True)

    def OnOpenRepository(self, e):
        repodir = wx.DirSelector("Open repository")
        if not repodir: return

        try:
            repo = Repository(repodir)
            new_win = MainWindow(repo)
            new_win.Show(True)
        except GitError, msg:
            wx.MessageBox(str(msg), 'Error', style=wx.OK|wx.ICON_ERROR)

    def OnExit(self, e):
        wx.TheApp.ExitApp()

    def OnAbout(self, e):
        ShowAboutDialog()

########NEW FILE########
__FILENAME__ = HistoryTab
import wx
import os
import os.path
import MainWindow
from CommitList import CommitList, EVT_COMMITLIST_SELECT, EVT_COMMITLIST_RIGHTCLICK
from DiffViewer import DiffViewer
from SwitchWizard import SwitchWizard
from Wizard import *
from FetchDialogs import FetchSetupDialog, FetchProgressDialog
from PushDialogs import PushSetupDialog, PushProgressDialog
import git
from git import GitError
from util import *
from wxutil import *

# Menu item ids
MENU_SWITCH_TO_COMMIT   = 10000
MENU_MERGE_COMMIT       = 10001
MENU_CHERRYPICK_COMMIT  = 10002
MENU_REVERT_COMMIT      = 10003

MENU_CREATE_BRANCH      = 11000
MENU_DELETE_BRANCH      = 12000

# This array is used to provide unique ids for menu items
# that refer to a branch
branch_indexes = []

class HistoryTab(object):
    def __init__(self, mainController):
        self.mainController = mainController
        self.mainWindow = self.mainController.frame
        
        # Commit list
        browserPanel = GetWidget(self.mainWindow, 'historyBrowserPanel')
        browserSizer = browserPanel.GetSizer()
        
        self.commitList = CommitList(browserPanel, -1, False)
        self.commitList.authorColumnPos = self.mainController.config.ReadInt('CommitListAuthorColumnPosition', 200)
        self.commitList.Bind(EVT_COMMITLIST_SELECT, self.OnCommitSelected, self.commitList)
        self.commitList.Bind(EVT_COMMITLIST_RIGHTCLICK, self.OnCommitRightClick, self.commitList)
        browserSizer.Add(self.commitList, 1, wx.EXPAND)
        
        # Diff viewer
        diffPanel = GetWidget(self.mainWindow, "historyDiffPanel")
        diffSizer = diffPanel.GetSizer()
        
        self.diffViewer = DiffViewer(diffPanel, -1)
        diffSizer.Add(self.diffViewer, 1, wx.EXPAND)
        
        # Splitter
        self.splitter = GetWidget(self.mainWindow, "historySplitter")

        # Context menu
        self.contextCommit = None
        self.contextMenu = wx.Menu()
        wx.EVT_MENU(self.mainWindow, MENU_SWITCH_TO_COMMIT, self.OnSwitchToCommit)
        wx.EVT_MENU(self.mainWindow, MENU_CREATE_BRANCH, self.OnCreateBranch)
        wx.EVT_MENU(self.mainWindow, MENU_MERGE_COMMIT, self.OnMerge)
        wx.EVT_MENU(self.mainWindow, MENU_CHERRYPICK_COMMIT, self.OnCherryPick)
        wx.EVT_MENU(self.mainWindow, MENU_REVERT_COMMIT, self.OnRevert)
        
        # Other events
        SetupEvents(self.mainWindow, [
            ('fetchTool', wx.EVT_TOOL, self.OnFetch),
            ('pushTool', wx.EVT_TOOL, self.OnPushCommit),
            ('switchTool', wx.EVT_TOOL, self.OnSwitchToCommit),
            ('switchMenuItem', wx.EVT_MENU, self.OnSwitchToCommit),
            ('createBranchMenuItem', wx.EVT_MENU, self.OnCreateBranch),
            ('mergeMenuItem', wx.EVT_MENU, self.OnMerge),
            ('cherryPickMenuItem', wx.EVT_MENU, self.OnCherryPick),
            ('revertMenuItem', wx.EVT_MENU, self.OnRevert),
            ('gotoCommitMenuItem', wx.EVT_MENU, self.OnGotoCommit),
        ])

    def OnCreated(self):
        self.splitter.SetSashPosition(self.mainController.config.ReadInt('HistorySplitterPosition', 200))

    def SetRepo(self, repo):
        # Branch indexes
        global branch_indexes
        for branch in repo.branches:
            if branch not in branch_indexes:
                branch_indexes.append(branch)

        # Menu events for branches
        for index in xrange(len(branch_indexes)):
            wx.EVT_MENU(self.mainWindow, MENU_DELETE_BRANCH + index, self.OnDeleteBranch)

        self.repo = repo
        self.commitList.SetRepo(repo)

        difftext = self.repo.run_cmd(['show', 'HEAD^'])
        self.diffViewer.Clear()

    def OnCommitSelected(self, e):
        self.contextCommit = self.commitList.CommitByRow(e.currentRow)

        # Show in diff viewer
        commit_diff = self.repo.run_cmd(['show', self.contextCommit.sha1])
        self.diffViewer.SetDiffText(commit_diff, commit_mode=True)

    def OnCommitRightClick(self, e):
        self.contextCommit = self.commitList.CommitByRow(e.currentRow)
        self.SetupContextMenu(self.contextCommit)
        self.commitList.PopupMenu(self.contextMenu, e.coords)

    def OnSwitchToCommit(self, e):
        if not self.contextCommit or self.mainController.selectedTab != MainWindow.TAB_HISTORY:
            return

        wizard = SwitchWizard(self.mainWindow, -1, self.repo, self.contextCommit)
        result = wizard.RunWizard()

        if result > 0:
            self.mainController.ReloadRepo()

            # Check for unmerged changes
            unmerged = False
            unstaged, staged = self.repo.get_status()
            for f in unstaged:
                if unstaged[f] == git.FILE_UNMERGED:
                    unmerged = True

            # Show error if checkout failed
            if wizard.error:
                wx.MessageBox(safe_unicode(wizard.error), 'Could not switch to this version', style=wx.OK|wx.ICON_ERROR)
                return

            # Show warning if necessary
            msg = ''
            if unmerged:
                msg = u'- Repository contains unmerged files. You have to merge them manually.'

            if wizard.submoduleWarnings:
                submodules = wizard.submoduleWarnings.keys()
                submodules.sort()

                if msg:
                    msg += '\n- '

                if len(submodules) == 1:
                    submodule = submodules[0]
                    msg += u"Submodule '%s' could not be switched to the referenced version:%s" \
                        % (submodule, safe_unicode(wizard.submoduleWarnings[submodule]))
                else:
                    msg += u"Some submodules could not be switched to the referenced version:\n\n"
                    for submodule in submodules:
                        msg += u"  - %s: %s\n" % (submodule, safe_unicode(wizard.submoduleReasons[submodule]))

            if msg:
                if len(msg.split('\n')) == 1:
                    msg = msg[2:] # remove '- ' from the beginning

                wx.MessageBox(msg, 'Warning', style=wx.OK|wx.ICON_ERROR)

    def OnCreateBranch(self, e):
        if not self.contextCommit or self.mainController.selectedTab != MainWindow.TAB_HISTORY:
            return

        dialog = wx.TextEntryDialog(self.mainWindow, "Enter branch name:", "Create branch...")
        if dialog.ShowModal() == wx.ID_OK:
            branch_name = dialog.GetValue()
            self.GitCommand(['branch', branch_name, self.contextCommit.sha1])

    def OnDeleteBranch(self, e):
        branch = branch_indexes[e.GetId() % 1000]
        msg = wx.MessageDialog(
            self.mainWindow,
            "By deleting branch '%s' all commits that are not referenced by another branch will be lost.\n\nDo you really want to continue?" % branch,
            "Warning",
            wx.ICON_EXCLAMATION | wx.YES_NO | wx.YES_DEFAULT
        )
        if msg.ShowModal() == wx.ID_YES:
            self.GitCommand(['branch', '-D', branch])

    def OnMerge(self, e):
        if not self.contextCommit or self.mainController.selectedTab != MainWindow.TAB_HISTORY:
            return

        # Default merge message
        if self.repo.current_branch:
            local_branch = self.repo.current_branch
        else:
            local_branch = "HEAD"

        remote_sha1 = self.contextCommit.sha1
        if remote_sha1 in self.repo.branches_by_sha1:
            remote_branch = "branch '%s'" % self.repo.branches_by_sha1[remote_sha1][0]
        elif remote_sha1 in self.repo.remote_branches_by_sha1:
            remote_branch = "remote branch '%s'" % self.repo.remote_branches_by_sha1[remote_sha1][0]
        else:
            remote_branch = "commit '%s'" % self.contextCommit.abbrev

        mergeMsg = "merge %s into %s" % (remote_branch, local_branch)

        # Show merge message dialog
        msg = wx.TextEntryDialog(
            self.mainWindow,
            "Enter merge message:",
            "Merge",
            mergeMsg,
            wx.ICON_QUESTION | wx.OK | wx.CANCEL
        )
        if msg.ShowModal() == wx.ID_OK:
            retcode, stdout, stderr = self.repo.run_cmd(['merge', self.contextCommit.sha1, '-m', mergeMsg], with_retcode=True, with_stderr=True)
            self.mainController.ReloadRepo()

            if retcode != 0:
                if 'CONFLICT' in stdout:
                    # Create MERGE_MSG
                    f = open(os.path.join(self.repo.dir, '.git', 'MERGE_MSG'), 'w')
                    f.write("%s\n\nConflicts:\n" % mergeMsg)
                    unstaged, staged = self.repo.get_status()
                    unmerged_files = [ fn for fn,status in unstaged.iteritems() if status == git.FILE_UNMERGED ]
                    for fn in unmerged_files:
                        f.write("\t%s\n" % fn)
                    f.close()

                    # Show warning
                    warningTitle = "Warning: conflicts during merge"
                    warningMsg = \
                        "Some files or submodules could not be automatically merged. " + \
                        "You have to resolve these conflicts by hand and then stage " + \
                        "these files/submodules.\n\n" + \
                        "If you want to abort merge, press \"Discard all changes\" on Index page."
                else:
                    warningTitle = "Error"
                    warningMsg = "Git returned the following error:\n\n" + stdout + stderr

                wx.MessageBox(warningMsg, warningTitle, style=wx.OK|wx.ICON_ERROR)

    def OnCherryPick(self, e):
        if not self.contextCommit or self.mainController.selectedTab != MainWindow.TAB_HISTORY:
            return

        confirmMsg = "Do you really want to cherry-pick this commit?"
        msg = wx.MessageDialog(
            self.mainWindow,
            confirmMsg,
            "Confirmation",
            wx.ICON_EXCLAMATION | wx.YES_NO | wx.YES_DEFAULT
        )
        if msg.ShowModal() == wx.ID_YES:
            retcode, stdout, stderr = self.repo.run_cmd(['cherry-pick', self.contextCommit.sha1], with_retcode=True, with_stderr=True)
            self.mainController.ReloadRepo()

            if retcode != 0:
                if 'Automatic cherry-pick failed' in stderr:
                    warningTitle = "Warning: conflicts during cherry-picking"
                    warningMsg = \
                        "Some files or submodules could not be automatically cherry-picked. " + \
                        "You have to resolve these conflicts by hand and then stage " + \
                        "these files/submodules.\n\n" + \
                        "If you want to abort cherry-picking, press \"Discard all changes\" on Index page."
                else:
                    warningTitle = "Error"
                    warningMsg = "Git returned the following error:\n\n" + stdout + stderr

                wx.MessageBox(warningMsg, warningTitle, style=wx.OK|wx.ICON_ERROR)

    def OnRevert(self, e):
        if not self.contextCommit or self.mainController.selectedTab != MainWindow.TAB_HISTORY:
            return

        confirmMsg = "Do you really want to revert this commit?"
        msg = wx.MessageDialog(
            self.mainWindow,
            confirmMsg,
            "Confirmation",
            wx.ICON_EXCLAMATION | wx.YES_NO | wx.YES_DEFAULT
        )
        if msg.ShowModal() == wx.ID_YES:
            retcode, stdout, stderr = self.repo.run_cmd(['revert', self.contextCommit.sha1], with_retcode=True, with_stderr=True)
            self.mainController.ReloadRepo()

            if retcode != 0:
                if 'Automatic reverting failed' in stderr:
                    warningTitle = "Warning: conflicts during reverting"
                    warningMsg = \
                        "Some files or submodules could not be automatically reverted. " + \
                        "You have to resolve these conflicts by hand and then stage " + \
                        "these files/submodules.\n\n" + \
                        "If you want to abort reverting, press \"Discard all changes\" on Index page."
                else:
                    warningTitle = "Error"
                    warningMsg = "Git returned the following error:\n\n" + stdout + stderr

                wx.MessageBox(warningMsg, warningTitle, style=wx.OK|wx.ICON_ERROR)

    def OnFetch(self, e):
        # Setup dialog
        setupDialog = FetchSetupDialog(self.mainWindow, -1, self.repo)
        result = setupDialog.ShowModal()

        # Progress dialog
        if result:
            progressDialog = FetchProgressDialog(self.mainWindow, -1, self.repo, setupDialog.selectedRemote, setupDialog.includeSubmodules, setupDialog.fetchTags)
            if progressDialog.ShowModal():
                self.mainController.ReloadRepo()

    def OnFetchProgress(self, eventType, eventParam):
        pass

    def OnPushCommit(self, e):
        # Require context commit
        if not self.contextCommit or self.mainController.selectedTab != MainWindow.TAB_HISTORY:
            wx.MessageBox(
                'Select the commit to be pushed first!',
                'Warning',
                style=wx.OK|wx.ICON_WARNING
            )
            return
        
        # Progress dialog
        setupDialog = PushSetupDialog(self.mainWindow, -1, self.repo)
        if setupDialog.ShowModal() == wx.ID_OK:
            remote = setupDialog.selectedRemote
            commit = self.contextCommit
            branch = setupDialog.selectedBranch
            forcePush = setupDialog.forcePush
            
            if len(remote) and len(branch):
                progressDialog = PushProgressDialog(self.mainWindow, -1, self.repo, remote, commit, branch, forcePush)
                if progressDialog.ShowModal():
                    self.mainController.ReloadRepo()

    def OnGotoCommit(self, e):
        if self.mainController.selectedTab != MainWindow.TAB_HISTORY:
            return

        msg = wx.TextEntryDialog(
            self.mainWindow,
            "Enter reference name or commit ID:",
            "Go to Version",
            "",
            wx.ICON_QUESTION | wx.OK | wx.CANCEL
        )
        msg.ShowModal()
        refname = msg.GetValue()
        
        if refname:
            commit_id = self.repo.run_cmd(['rev-parse', refname]).strip()
            if commit_id:
                error = self.commitList.GotoCommit(commit_id)
            else:
                error = "Cannot find reference or commit ID: '%s'" % refname

            if error:
                wx.MessageBox(
                    error,
                    "Error",
                    style=wx.OK|wx.ICON_ERROR
                )

    def SaveState(self):
        self.mainController.config.WriteInt('HistorySplitterPosition', self.splitter.GetSashPosition())
        self.mainController.config.WriteInt('CommitListAuthorColumnPosition', self.commitList.authorColumnPos)

    def SetupContextMenu(self, commit):
        branches = self.repo.branches_by_sha1.get(commit.sha1, [])

        # Delete old items
        menuItems = self.contextMenu.GetMenuItems()
        for item in menuItems:
            self.contextMenu.Delete(item.GetId())

        # Switch to this version...
        self.contextMenu.Append(MENU_SWITCH_TO_COMMIT, "Switch to this version...")

        # Create branch
        self.contextMenu.Append(MENU_CREATE_BRANCH, "Create branch here...")

        # Delete branch
        if branches:
            self.contextMenu.AppendSeparator()

            for branch in branches:
                menu_id = MENU_DELETE_BRANCH + branch_indexes.index(branch)
                self.contextMenu.Append(menu_id, "Delete branch '%s'" % branch)

        # Merge
        self.contextMenu.AppendSeparator()
        self.contextMenu.Append(MENU_MERGE_COMMIT, "Merge into current HEAD")

        # Cherry-pick
        self.contextMenu.Append(MENU_CHERRYPICK_COMMIT, "Apply this commit to HEAD (cherry-pick)")
        self.contextMenu.Append(MENU_REVERT_COMMIT, "Apply the inverse of this commit to HEAD (revert)")

    def GitCommand(self, cmd, check_submodules=False, **opts):
        try:
            retval = self.repo.run_cmd(cmd, raise_error=True, **opts)
            self.mainController.ReloadRepo()

            # Check submodules
            if check_submodules and self.repo.submodules:
                for submodule in self.repo.submodules:
                    if submodule.main_ref != submodule.head:
                        wx.MessageBox(
                            "One or more submodule versions differ from the version " +
                            "that is referenced by the current HEAD. If this is not " +
                            "what you want, you need to checkout them to the proper version.",
                            'Warning',
                            style=wx.OK|wx.ICON_WARNING
                        )
                        break

            return retval
        except GitError, msg:
            wx.MessageBox(str(msg), 'Error', style=wx.OK|wx.ICON_ERROR)
            return False


########NEW FILE########
__FILENAME__ = IndexTab
# -*- encoding: utf-8

import wx
import wx.html
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin, ListCtrlSelectionManagerMix
import os, os.path
import sys

import MainWindow
import Wizard
from DiffViewer import DiffViewer
from git import *
from util import *
from wxutil import *

MOD_DESCS = {
    FILE_ADDED       : 'added',
    FILE_MODIFIED    : 'modified',
    FILE_DELETED     : 'deleted',
    FILE_COPIED      : 'copied',
    FILE_RENAMED     : 'renamed',
    FILE_UNMERGED    : 'unmerged',
    FILE_TYPECHANGED : 'type changed',
    FILE_UNTRACKED   : 'untracked',
    FILE_BROKEN      : 'BROKEN',
    FILE_UNKNOWN     : 'UNKNOWN'
}

if sys.platform in ['win32', 'cygwin']:
    LABEL_STAGE = u"Stage >"
    LABEL_UNSTAGE = u"< Unstage"
    LABEL_DISCARD = u"× Discard"
else:
    LABEL_STAGE = u"Stage ⇒"
    LABEL_UNSTAGE = u"⇐ Unstage"
    LABEL_DISCARD = u"× Discard"

MENU_MERGE_FILE     = 20000
MENU_TAKE_LOCAL     = 20001
MENU_TAKE_REMOTE    = 20002

class FileList(wx.ListCtrl, ListCtrlAutoWidthMixin, ListCtrlSelectionManagerMix):
    def __init__(self, parent, ID, pos=wx.DefaultPosition, size=wx.DefaultSize, style=wx.LC_REPORT | wx.LC_NO_HEADER):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        ListCtrlAutoWidthMixin.__init__(self)
        ListCtrlSelectionManagerMix.__init__(self)

        self.InsertColumn(0, "File")

    def GetSelections(self):
        return [ i for i in xrange(self.GetItemCount()) if self.GetItemState(i, wx.LIST_STATE_SELECTED) == wx.LIST_STATE_SELECTED ]

class IndexTab(object):
    def __init__(self, mainController):
        self.mainController = mainController
        self.mainWindow = mainController.frame
        self.listPanel = GetWidget(self.mainWindow, 'indexListPanel')
        self.listSizer = self.listPanel.GetSizer()
        
        # Splitter
        self.splitter = GetWidget(self.mainWindow, 'indexSplitter')
        
        # Unstaged list
        self.unstagedList = FileList(self.listPanel, -1)
        unstagedSizer = self.listPanel.GetSizer().GetItem(0).GetSizer()
        unstagedSizer.Add(self.unstagedList, 1, wx.EXPAND|wx.ALL, 0)
        self.unstagedList.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnUnstagedListSelect, self.unstagedList)
        self.unstagedList.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.OnUnstagedRightClick, self.unstagedList)
        self.listPanel.Layout()

        self.unstagedMenu = wx.Menu()
        self.unstagedMenu.Append(MENU_MERGE_FILE, "Merge file")
        self.unstagedMenu.Append(MENU_TAKE_LOCAL, "Take local version")
        self.unstagedMenu.Append(MENU_TAKE_REMOTE, "Take remote version")
        wx.EVT_MENU(self.mainWindow, MENU_MERGE_FILE, self.OnMergeFile)
        wx.EVT_MENU(self.mainWindow, MENU_TAKE_LOCAL, self.OnTakeLocal)
        wx.EVT_MENU(self.mainWindow, MENU_TAKE_REMOTE, self.OnTakeRemote)

        # Staged changes
        self.stagedList = FileList(self.listPanel, -1)
        stagedSizer = self.listPanel.GetSizer().GetItem(2).GetSizer()
        stagedSizer.Add(self.stagedList, 1, wx.EXPAND|wx.ALL, 0)
        self.stagedList.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnStagedListSelect, self.stagedList)
        self.listPanel.Layout()

        # Diff viewer
        diffPanel = GetWidget(self.mainWindow, 'indexDiffPanel')
        diffSizer = diffPanel.GetSizer()

        self.diffViewer = DiffViewer(diffPanel, -1)
        diffSizer.Add(self.diffViewer, 1, wx.EXPAND)
        diffPanel.Layout()
        
        # Events
        SetupEvents(self.mainWindow, [
            ('stageButton', wx.EVT_BUTTON, self.OnStage),
            ('unstageButton', wx.EVT_BUTTON, self.OnUnstage),
            ('discardButton', wx.EVT_BUTTON, self.OnDiscard),
            ('commitTool', wx.EVT_TOOL, self.OnCommit),
            ('resetTool', wx.EVT_TOOL, self.OnReset),
            
            ('stageMenuItem', wx.EVT_MENU, self.OnStage),
            ('unstageMenuItem', wx.EVT_MENU, self.OnUnstage),
            ('discardMenuItem', wx.EVT_MENU, self.OnDiscard),
            ('commitMenuItem', wx.EVT_MENU, self.OnCommit),
            ('resetMenuItem', wx.EVT_MENU, self.OnReset),
        ])

    def OnCreated(self):
        self.splitter.SetSashPosition(self.mainController.config.ReadInt('IndexSplitterPosition', 200))
        self.splitter.SetMinimumPaneSize(120)

    def OnStage(self, e):
        if self.mainController.selectedTab != MainWindow.TAB_INDEX:
            return

        selection = self.unstagedList.GetSelections()

        for row in selection:
            filename, change = self.unstagedChanges[row]
            if change == FILE_DELETED:
                self.repo.run_cmd(['rm', '--cached', filename])
            else:
                self.repo.run_cmd(['add', filename])
        
        self.Refresh()

        if len(selection) > 0:
            row = selection[0]
            if self.unstagedList.GetItemCount() > row:
                self.unstagedList.SetItemState(row, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)

    def OnUnstage(self, e):
        if self.mainController.selectedTab != MainWindow.TAB_INDEX:
            return

        selection = self.stagedList.GetSelections()

        for row in self.stagedList.GetSelections():
            filename = self.stagedChanges[row][0]
            if self.repo.head == 'HEAD':
                self.repo.run_cmd(['rm', '--cached', filename])
            else:
                self.repo.run_cmd(['reset', 'HEAD', filename])

        self.Refresh()

        if len(selection) > 0:
            row = selection[0]
            if self.stagedList.GetItemCount() > row:
                self.stagedList.SetItemState(row, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)

    def OnDiscard(self, e):
        if self.mainController.selectedTab != MainWindow.TAB_INDEX:
            return

        # Get selection
        rows = self.unstagedList.GetSelections()
        if len(rows) == 0:
            return

        # Confirm dialog
        msg = wx.MessageDialog(
            self.mainWindow,
            "The selected changes will be permanently lost. Do you really want to continue?",
            "Warning",
            wx.ICON_EXCLAMATION | wx.YES_NO | wx.YES_DEFAULT
        )
        if msg.ShowModal() == wx.ID_YES:
            for row in rows:
                filename = self.unstagedChanges[row][0]
                if filename in self.untrackedFiles:
                    try: os.unlink(os.path.join(self.repo.dir, filename))
                    except OSError: pass
                else:
                    self.repo.run_cmd(['checkout', filename])

        self.Refresh()

    def OnUnstagedListSelect(self, e):
        # Clear selection in stagedList
        for row in self.stagedList.GetSelections():
            self.stagedList.SetItemState(row, 0, wx.LIST_STATE_SELECTED)

        # Show diffs
        selection = self.unstagedList.GetSelections()

        diff_text = ''
        for row in selection:
            filename = self.unstagedChanges[row][0]
            if filename in self.untrackedFiles:
                filename = os.path.join(self.repo.dir, filename)
                diff_text += diff_for_untracked_file(filename)
            else:
                diff_text += self.repo.run_cmd(['diff', self.unstagedChanges[row][0]])

        self.diffViewer.SetDiffText(diff_text)

    def OnStagedListSelect(self, e):
        # Clear selection in unstagedList
        for row in self.unstagedList.GetSelections():
            self.unstagedList.SetItemState(row, 0, wx.LIST_STATE_SELECTED)

        # Show diffs
        selection = self.stagedList.GetSelections()

        diff_text = ''
        for row in selection:
            diff_text += self.repo.run_cmd(['diff', '--cached', self.stagedChanges[row][0]])

        self.diffViewer.SetDiffText(diff_text)

    def OnUnstagedRightClick(self, e):
        id = self.selectedUnstagedItem = e.GetIndex()
        filename, modification = self.unstagedChanges[id]
        submodule_names = [ r.name for r in self.repo.submodules ]

        if modification == FILE_UNMERGED and filename not in submodule_names:
            self.mainWindow.PopupMenu(self.unstagedMenu)

    def OnCommit(self, e):
        if len(self.stagedChanges) == 0 and not os.path.exists(os.path.join(self.repo.dir, '.git', 'MERGE_HEAD')):
            wx.MessageBox(
                "Stage some files on Changes tab before committing!",
                "Nothing to commit.",
                style=wx.ICON_EXCLAMATION | wx.OK
            )
            return

        if len([c for f,c in self.unstagedChanges if c == FILE_UNMERGED]):
            wx.MessageBox(
                "You should fix conflicts before committing!",
                "Error",
                style=wx.ICON_EXCLAMATION | wx.OK
            )
            return

        # Show commit wizard
        commit_wizard = CommitWizard(self.mainWindow, -1, self.repo)
        commit_wizard.RunWizard()
        self.mainController.SetRepo(self.repo)

    def OnReset(self, e):
        msg = wx.MessageDialog(
            self.mainWindow,
            "This operation will discard ALL (both staged and unstaged) changes. Do you really want to continue?",
            "Warning",
            wx.ICON_EXCLAMATION | wx.YES_NO | wx.YES_DEFAULT
        )
        if msg.ShowModal() == wx.ID_YES:
            self.repo.run_cmd(['reset', '--hard'])
            self.repo.run_cmd(['clean', '-f'])

            self.Refresh()

    def OnMergeFile(self, e):
        self.repo.merge_file(self.unstagedChanges[self.selectedUnstagedItem][0])

    def _simpleMerge(self, filename, msg, index):
        msg = wx.MessageDialog(
            self.mainWindow,
            msg,
            "Warning",
            wx.ICON_EXCLAMATION | wx.YES_NO | wx.YES_DEFAULT
        )
        if msg.ShowModal() == wx.ID_YES:
            try:
                content = self.repo.run_cmd(['cat-file', 'blob', ':%d:%s' % (index, filename)], raise_error=True)
                f = open(os.path.join(self.repo.dir, filename), 'wb')
                f.write(content)
                f.close()
                self.repo.run_cmd(['add', filename], raise_error=True)
            except GitError, e:
                wx.MessageBox(safe_unicode(e), "Error", style=wx.OK|wx.ICON_ERROR)
            except OSError, e:
                wx.MessageBox(safe_unicode(e), "Error", style=wx.OK|wx.ICON_ERROR)

        self.Refresh()

    def OnTakeLocal(self, e):
        filename = self.unstagedChanges[self.selectedUnstagedItem][0]

        msg = "You are about to stage the HEAD version of file '%s' " \
            "and discard any modifications from the merged commit.\n\n" \
            "Do you want to continue?" % filename

        self._simpleMerge(filename, msg, 2)

    def OnTakeRemote(self, e):
        filename = self.unstagedChanges[self.selectedUnstagedItem][0]

        msg = "You are about to stage the MERGE_HEAD version of file '%s' " \
            "and discard the version that is in the current HEAD.\n\n" \
            "Do you want to continue?" % filename

        self._simpleMerge(filename, msg, 3)

    def SetRepo(self, repo):
        self.repo = repo
        unstagedDict, stagedDict = self.repo.get_status()

        # Unstaged changes
        unstagedFiles = unstagedDict.keys()
        unstagedFiles.sort()
        self.unstagedChanges = [ (f,unstagedDict[f]) for f in unstagedFiles ]

        self.unstagedList.DeleteAllItems()
        for c in self.unstagedChanges:
            pos = self.unstagedList.GetItemCount()
            self.unstagedList.InsertStringItem(pos, '%s (%s)' % (c[0], MOD_DESCS[c[1]]))

        # Unstaged changes
        stagedFiles = stagedDict.keys()
        stagedFiles.sort()
        self.stagedChanges = [ (f,stagedDict[f]) for f in stagedFiles ]

        self.stagedList.DeleteAllItems()
        for c in self.stagedChanges:
            pos = self.stagedList.GetItemCount()
            self.stagedList.InsertStringItem(pos, '%s (%s)' % (c[0], MOD_DESCS[c[1]]))

        # Untracked files
        self.untrackedFiles = [ f for f in unstagedDict if unstagedDict[f] == FILE_UNTRACKED ]

    def Refresh(self):
        self.SetRepo(self.repo)

    def SaveState(self):
        self.mainController.config.WriteInt('IndexSplitterPosition', self.splitter.GetSashPosition())

    def _parse_diff_output(self, cmd):
        output = self.repo.run_cmd(cmd)
        result = []

        items = output.split('\x00')
        for i in xrange(len(items)/2):
            mod, filename = items[2*i], items[2*i+1]
            old_mode, new_mode, old_sha1, new_sha1, mod_type = mod.split(' ')
            result.append((filename, mod_type[0]))

        return result

class CommitWizard(Wizard.Wizard):
    def __init__(self, parent, id, repo):
        Wizard.Wizard.__init__(self, parent, id)
        self.repo = repo

        # --- Detached head warning page ---
        self.detachedWarningPage = self.CreateWarningPage(
            "Warning: committing to a detached HEAD",

            "Your HEAD is not connected with a local branch. If you commit and then " +
            "checkout to a different version later, your commit will be lost.\n\n" +
            "Do you still want to continue?",

            [Wizard.BTN_CANCEL, Wizard.BTN_CONTINUE]
        )

        # --- Modified submodules warning page ---
        self.submoduleWarningPage = self.CreateWarningPage(
            "Warning: uncommitted changes in submodules",

            "There are uncommitted changes in one or more submodules.\n\n" +
            "If you want these changes to be saved in this version, " +
            "commit the submodules first, then stage the new submodule versions " +
            "to the main module.\n\n" +
            "Do you still want to continue?",

            [Wizard.BTN_CANCEL, Wizard.BTN_CONTINUE]
        )

        # --- Commit page ---
        self.commitPage = self.CreatePage(
            "Commit staged changes",
            [Wizard.BTN_CANCEL, Wizard.BTN_FINISH]
        )
        s = self.commitPage.sizer

        # Author
        s.Add(wx.StaticText(self.commitPage, -1, "Author:"), 0, wx.TOP, 5)

        authorSizer = wx.BoxSizer(wx.HORIZONTAL)
        s.Add(authorSizer, 0, wx.EXPAND)

        self.authorEntry = wx.TextCtrl(self.commitPage, -1, style=wx.TE_READONLY)
        authorSizer.Add(self.authorEntry, 1, wx.ALL, 5)

        self.changeAuthorBtn = wx.Button(self.commitPage, -1, 'Change')
        self.Bind(wx.EVT_BUTTON, self.OnAuthorChange, self.changeAuthorBtn)
        authorSizer.Add(self.changeAuthorBtn, 0, wx.ALL, 5)
        
        # Short message
        s.Add(wx.StaticText(self.commitPage, -1, "Commit description:"), 0, wx.TOP, 5)
        self.shortmsgEntry = wx.TextCtrl(self.commitPage, -1)
        s.Add(self.shortmsgEntry, 0, wx.EXPAND | wx.ALL, 5)

        # Details
        s.Add(wx.StaticText(self.commitPage, -1, "Commit details:"), 0, wx.TOP, 5)
        self.detailsEntry = wx.TextCtrl(self.commitPage, -1, style=wx.TE_MULTILINE)
        s.Add(self.detailsEntry, 1, wx.EXPAND | wx.ALL, 5)

        # Amend
        self.amendChk = wx.CheckBox(self.commitPage, -1, "Amend (add to previous commit)")
        s.Add(self.amendChk, 0, wx.EXPAND | wx.ALL, 5)
        self.Bind(wx.EVT_CHECKBOX, self.OnAmendChk, self.amendChk)

        # Get HEAD info for amending
        try:
            output = self.repo.run_cmd(['log', '-1', '--pretty=format:%an%x00%ae%x00%s%x00%b'], raise_error=True)
            self.amendAuthorName, self.amendAuthorEmail, self.amendShortMsg, self.amendDetails = output.split('\x00')
        except GitError:
            self.amendChk.Disable()

    def OnStart(self):
        # Check whether submodules have changes
        self.hasSubmoduleChanges = False
        for module in self.repo.submodules:
            unstagedChanges, stagedChanges = module.get_status()
            if unstagedChanges or stagedChanges:
                self.hasSubmoduleChanges = True
                break

        # Check whether HEAD is detached
        self.isDetachedHead = (self.repo.current_branch == None)

        # Get default commit message from MERGE_MSG
        mergemsg_file = os.path.join(self.repo.dir, '.git', 'MERGE_MSG')
        if os.path.exists(mergemsg_file):
            # Short msg
            f = open(mergemsg_file)
            self.currentShortMsg = safe_unicode(f.readline())

            # Details
            self.currentDetails = u''
            sep = f.readline()
            if sep.strip():
                self.currentDetails += safe_unicode(sep)
            self.currentDetails += safe_unicode(f.read())
            f.close()

            # Write into text fields
            self.shortmsgEntry.SetValue(self.currentShortMsg)
            self.detailsEntry.SetValue(self.currentDetails)

        # Get author info
        self.authorName  = self.repo.run_cmd(['config', 'user.name']).strip()
        self.authorEmail = self.repo.run_cmd(['config', 'user.email']).strip()
        self.UpdateAuthorEntry()

        # Show first page
        if self.isDetachedHead:
            self.SetPage(self.detachedWarningPage)
        elif self.hasSubmoduleChanges:
            self.SetPage(self.submoduleWarningPage)
        else:
            self.SetPage(self.commitPage)

    def OnAuthorChange(self, e):
        # Show author dialog
        dialog = AuthorDialog(self, -1, self.authorName, self.authorEmail)

        if dialog.ShowModal():
            self.authorName = dialog.authorName
            self.authorEmail = dialog.authorEmail

            # Save new author if necessary
            if dialog.saveMode == AUTHOR_PROJECT_DEFAULT:
                self.repo.run_cmd(['config', 'user.name', self.authorName])
                self.repo.run_cmd(['config', 'user.email', self.authorEmail])
            elif dialog.saveMode == AUTHOR_GLOBAL_DEFAULT:
                self.repo.run_cmd(['config', '--global', 'user.name', self.authorName])
                self.repo.run_cmd(['config', '--global', 'user.email', self.authorEmail])

        # Update author entry
        self.UpdateAuthorEntry()

    def UpdateAuthorEntry(self, name=None, email=None):
        if name == None:
            name = self.authorName
        if email == None:
            email = self.authorEmail

        self.authorEntry.SetValue(u"%s <%s>" % (safe_unicode(name), safe_unicode(email)))

    def OnAmendChk(self, e):
        is_amend = self.amendChk.GetValue()

        if is_amend:
            # Save current commit message
            self.currentShortMsg = self.shortmsgEntry.GetValue()
            self.currentDetails = self.detailsEntry.GetValue()

            # Replace commit message with the one in HEAD
            self.shortmsgEntry.SetValue(safe_unicode(self.amendShortMsg))
            self.detailsEntry.SetValue(safe_unicode(self.amendDetails))

            # Replace author, disable author change
            self.UpdateAuthorEntry(self.amendAuthorName, self.amendAuthorEmail)
            self.changeAuthorBtn.Disable()
        else:
            # Save modified amend message
            self.amendShortMsg = self.shortmsgEntry.GetValue()
            self.amendDetails = self.detailsEntry.GetValue()

            # Write back old commit message
            self.shortmsgEntry.SetValue(safe_unicode(self.currentShortMsg))
            self.detailsEntry.SetValue(safe_unicode(self.currentDetails))

            # Write back chosen author, enable author change
            self.UpdateAuthorEntry()
            self.changeAuthorBtn.Enable()

    def OnButtonClicked(self, button):
        if button == Wizard.BTN_CANCEL:
            self.EndWizard(0)
        
        if self.currentPage == self.detachedWarningPage:
            if self.hasSubmoduleChanges:
                self.SetPage(self.submoduleWarningPage)
            else:
                self.SetPage(self.commitPage)
        elif self.currentPage == self.submoduleWarningPage:
            self.SetPage(self.commitPage)

        # Commit page
        elif self.currentPage == self.commitPage:
            if button == Wizard.BTN_PREV:
                self.SetPage(self.submoduleWarningPage)
            elif button == Wizard.BTN_FINISH:
                if self.Validate():
                    # Commit changes
                    short_msg = self.shortmsgEntry.GetValue()
                    details = self.detailsEntry.GetValue()
                    is_amend = self.amendChk.GetValue()

                    if len(details.strip()):
                        msg = "%s\n\n%s" % (short_msg, details)
                    else:
                        msg = short_msg

                    try:
                        self.repo.commit(self.authorName, self.authorEmail, msg, amend=is_amend)
                    except GitError, msg:
                        wx.MessageBox(
                            safe_unicode(msg),
                            "Error",
                            style=wx.ICON_ERROR | wx.OK
                        )
                        
                    self.EndWizard(0)
                else:
                    # Show alert
                    if len(self.authorName) == 0 or len(self.authorEmail) == 0:
                        errormsg = "Please set author name!"
                    else:
                        errormsg = "Please fill in commit description!"

                    msg = wx.MessageDialog(
                        self,
                        errormsg,
                        "Notice",
                        wx.ICON_EXCLAMATION | wx.OK
                    )
                    msg.ShowModal()

    def Validate(self):
        return len(self.authorName) != 0 and len(self.authorEmail) != 0 and \
            len(self.shortmsgEntry.GetValue()) != 0

AUTHOR_NOT_DEFAULT     = 0
AUTHOR_PROJECT_DEFAULT = 1
AUTHOR_GLOBAL_DEFAULT  = 2

class AuthorDialog(wx.Dialog):
    def __init__(self, parent, id, default_name, default_email):
        wx.Dialog.__init__(self, parent, id, size=(350,280), title="Change author...")

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        self.authorName = default_name
        self.authorEmail = default_email
        self.saveMode = AUTHOR_NOT_DEFAULT

        # Name
        self.sizer.Add(wx.StaticText(self, -1, "Name:"), 0, wx.ALL, 5)
        self.nameEntry = wx.TextCtrl(self, -1)
        self.nameEntry.SetValue(default_name)
        self.sizer.Add(self.nameEntry, 0, wx.EXPAND | wx.ALL, 5)

        # Email
        self.sizer.Add(wx.StaticText(self, -1, "E-mail:"), 0, wx.ALL, 5)
        self.emailEntry = wx.TextCtrl(self, -1)
        self.emailEntry.SetValue(default_email)
        self.sizer.Add(self.emailEntry, 0, wx.EXPAND | wx.ALL, 5)

        # Save mode
        self.saveModeBtns = wx.RadioBox(self, -1, "Save mode:", 
            style=wx.RA_SPECIFY_ROWS,
            choices=["Use only for this commit",
                     "Save as project default",
                     "Save as global default"]
        )
        self.sizer.Add(self.saveModeBtns, 1, wx.EXPAND | wx.ALL, 5)

        # Finish buttons
        self.buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(self.buttonSizer, 0, wx.ALL | wx.ALIGN_RIGHT, 5)

        self.okBtn = wx.Button(self, -1, 'OK')
        self.buttonSizer.Add(self.okBtn, 1, wx.ALL, 5)
        self.Bind(wx.EVT_BUTTON, self.OnOk, self.okBtn)

        self.cancelBtn = wx.Button(self, -1, 'Cancel')
        self.buttonSizer.Add(self.cancelBtn, 1, wx.ALL, 5)
        self.Bind(wx.EVT_BUTTON, self.OnCancel, self.cancelBtn)

    def OnOk(self, e):
        name = self.nameEntry.GetValue().strip()
        email = self.emailEntry.GetValue().strip()

        if name and email:
            self.authorName = name
            self.authorEmail = email
            self.saveMode = self.saveModeBtns.GetSelection()
            self.EndModal(1)

    def OnCancel(self, e):
        self.EndModal(0)


########NEW FILE########
__FILENAME__ = MainWindow
# -*- coding: utf-8
from git import *
from HistoryTab import HistoryTab
from IndexTab import IndexTab
from AboutDialog import ShowAboutDialog
import wx
from wx import xrc
from wxutil import *

ID_NEWWINDOW    = 101
ID_CLOSEWINDOW  = 102

TAB_HISTORY     = 0
TAB_INDEX       = 1

class MainWindow(object):
    def __init__(self, repo):
        # Load frame from XRC
        self.frame = LoadFrame(None, 'MainWindow')
        
        # Read default window size
        self.config = wx.Config('stupidgit')
        width = self.config.ReadInt('MainWindowWidth', 550)
        height = self.config.ReadInt('MainWindowHeight', 650)
        self.frame.SetSize((width, height))
        
        # Create module choice
        toolbar = self.frame.GetToolBar()
        self.moduleChoice = wx.Choice(toolbar, -1)
        if sys.platform == 'darwin':
            # Don't ask me why, but that's how the control is positioned to middle...
            self.moduleChoice.SetSize((200,15))
        else:
            self.moduleChoice.SetSize((200,-1))
        
        self.moduleChoice.Bind(wx.EVT_CHOICE, self.OnModuleChosen)
        toolbar.InsertControl(0, self.moduleChoice)
        toolbar.Realize()
        
        # Setup events
        SetupEvents(self.frame, [
            (None, wx.EVT_CLOSE, self.OnWindowClosed),
            
            ('tabs', wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnTabChanged),

            ('quitMenuItem', wx.EVT_MENU, self.OnExit),
            ('openMenuItem', wx.EVT_MENU, self.OnOpenRepository),
            ('newWindowMenuItem', wx.EVT_MENU, self.OnNewWindow),
            ('closeWindowMenuItem', wx.EVT_MENU, self.OnCloseWindow),
            ('aboutMenuItem', wx.EVT_MENU, self.OnAbout),
            ('refreshMenuItem', wx.EVT_MENU, self.OnRefresh),

            ('refreshTool', wx.EVT_TOOL, self.OnRefresh),
            ('refreshButton', wx.EVT_BUTTON, self.OnRefresh),
        ])
        
        # Setup tabs
        self.historyTab = HistoryTab(self)
        self.indexTab = IndexTab(self)
        self.selectedTab = 0

        # Load repository
        self.SetMainRepo(repo)

    def Show(self, doShow=True):
        self.frame.Show(doShow)
        
        # Sash positions must be set after the window is really shown.
        # Otherwise the sash position settings will be silently ignored :-/
        if doShow:
            self.OnWindowCreated(None)

    def OnNewWindow(self, e):
        win = MainWindow(None)
        win.Show(True)

    def OnWindowCreated(self, e):
        wx.TheApp.OnWindowCreated(self)
        self.indexTab.OnCreated()
        self.historyTab.OnCreated()

    def OnCloseWindow(self, e):
        self.frame.Close()

    def OnWindowClosed(self, e):
        # Save window geometry
        size = self.frame.GetSize()
        self.config.WriteInt('MainWindowWidth', size.GetWidth())
        self.config.WriteInt('MainWindowHeight', size.GetHeight())
        self.historyTab.SaveState()
        self.indexTab.SaveState()

        # Close window
        self.frame.Destroy()
        wx.TheApp.OnWindowClosed(self)

    def OnOpenRepository(self, e):
        repodir = wx.DirSelector("Open repository")
        if not repodir: return

        try:
            repo = Repository(repodir)

            if self.mainRepo:
                new_win = MainWindow(repo)
                new_win.Show(True)
            else:
                self.SetMainRepo(repo)
        except GitError, msg:
            wx.MessageBox(str(msg), 'Error', style=wx.OK|wx.ICON_ERROR)

    def OnTabChanged(self, e):
        self.selectedTab = e.GetSelection()

    def OnAbout(self, e):
        ShowAboutDialog()

    def OnExit(self, e):
        wx.TheApp.ExitApp()

    def SetMainRepo(self, repo):
        self.mainRepo = repo

        if repo:
            title = "stupidgit - %s" % os.path.basename(repo.dir)

            for module in self.mainRepo.all_modules:
                self.moduleChoice.Append(module.name)
            
            self.moduleChoice.Select(0)
            self.SetRepo(repo)

        else:
            title = "stupidgit"
            self.currentRepo = None

        self.frame.SetTitle(title)

    def SetRepo(self, repo):
        self.currentRepo = repo
        self.currentRepo.load_refs()
        self.historyTab.SetRepo(repo)
        self.indexTab.SetRepo(repo)

    def ReloadRepo(self):
        self.currentRepo.load_refs()
        self.SetRepo(self.currentRepo)

        # Load referenced version in submodules
        for submodule in self.currentRepo.submodules:
            submodule.load_refs()

    def OnModuleChosen(self, e):
        module_name = e.GetString()
        module = [m for m in self.mainRepo.all_modules if m.name == module_name]
        if module:
            self.SetRepo(module[0])

    def OnRefresh(self, e):
        self.currentRepo.load_refs()
        self.SetRepo(self.currentRepo)


########NEW FILE########
__FILENAME__ = PasswordDialog
import wx

class PasswordDialog(wx.Dialog):
    def __init__(self, parent, id, title):
        wx.Dialog.__init__(self, parent, id)
        self.SetTitle('SSH authentication')

        if not title:
            title = 'Password:'
        self.password = None

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        txt = wx.StaticText(self, -1, title)
        sizer.Add(txt, 1, wx.EXPAND | wx.ALL, 10)

        self.passwordEntry = wx.TextCtrl(self, -1, style=wx.TE_PASSWORD | wx.TE_PROCESS_ENTER)
        self.passwordEntry.Bind(wx.EVT_TEXT_ENTER, self.OnOk)
        sizer.Add(self.passwordEntry, 0, wx.EXPAND | wx.ALL, 10)

        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(btnSizer, 0, wx.EXPAND | wx.ALL, 10)

        btnOk = wx.Button(self, -1, 'OK')
        btnOk.Bind(wx.EVT_BUTTON, self.OnOk)
        btnSizer.Add(btnOk, 0, wx.EXPAND | wx.RIGHT, 5)

        btnCancel = wx.Button(self, -1, 'Cancel')
        btnCancel.Bind(wx.EVT_BUTTON, self.OnCancel)
        btnSizer.Add(btnCancel, 0, wx.EXPAND | wx.LEFT, 5)

        self.Fit()

    def OnOk(self, e):
        self.password = self.passwordEntry.GetValue()
        self.EndModal(1)

    def OnCancel(self, e):
        self.EndModal(0)


########NEW FILE########
__FILENAME__ = platformspec
import sys
import os
import wx

platform = None
default_font = None

# Init non-GUI specific parts
def init():
    global platform

    if not platform:
        # Determine platform name
        if sys.platform in ['win32', 'cygwin']:
            platform = 'win'
        elif sys.platform == 'darwin':
            platform = 'osx'
        elif os.name == 'posix':
            platform = 'unix' # I know, OSX is unix, too :)
        else:
            platform = 'other'

# Init platform-specific values
def init_wx():
    global default_font
        
    # Fonts
    default_font = wx.SystemSettings_GetFont(wx.SYS_DEFAULT_GUI_FONT)

# Font creator that solves the headache with pixel sizes
# - in most cases...
def Font(size, family=None, style=wx.FONTSTYLE_NORMAL, weight=wx.FONTWEIGHT_NORMAL):
    init_wx()

    if not family:
        family = default_font.GetFamily()
    
    font = wx.Font(size, family, style, weight)
    if platform == 'win':
        font.SetPixelSize((size*2,size))

    return font

# Initialize module
init()


########NEW FILE########
__FILENAME__ = PushDialogs
import wx
from wxutil import *
from util import *
from git import *

class PushSetupDialog(object):
    def __init__(self, parent, id, repo):
        self.dialog = LoadDialog(parent, 'PushDialog')
        self.dialog.SetMinSize((400, -1))
        self.repo = repo
        
        # Widgets
        self.remoteChooser = GetWidget(self.dialog, 'remoteChooser')
        self.branchChooser = GetWidget(self.dialog, 'branchChooser')
        self.branchEntry = GetWidget(self.dialog, 'branchEntry')
        self.warningLabel = GetWidget(self.dialog, 'warningLabel')
        self.detailsButton = GetWidget(self.dialog, 'detailsButton')
        self.forcePushCheckbox = GetWidget(self.dialog, 'forcePushCheckbox')
        
        # Events
        SetupEvents(self.dialog, [
            ('remoteChooser', wx.EVT_CHOICE, self.OnRemoteChosen),
            ('branchChooser', wx.EVT_CHOICE, self.OnBranchChosen),
            ('branchEntry', wx.EVT_TEXT, self.OnBranchText),
            ('forcePushCheckbox', wx.EVT_CHECKBOX, self.OnForcePush)
        ])
        
        # Setup remotes
        self.remoteChoices = [name for name,url in self.repo.remotes.iteritems()]
        self.remoteChoices.sort()
        
        self.remoteChooser = GetWidget(self.dialog, 'remoteChooser')
        for remote in self.remoteChoices:
            self.remoteChooser.Append(remote)
        self.remoteChooser.Select(0)
        self.OnRemoteChosen()
        
        # Setup initial settings
        self.forcePush = False
        self.HideWarning()

    def ShowModal(self):
        self.dialog.Fit()
        return self.dialog.ShowModal()

    def OnRemoteChosen(self, e=None):
        remoteIndex = self.remoteChooser.GetSelection()
        self.selectedRemote = self.remoteChoices[remoteIndex]
        
        # Update branches
        prefix = '%s/' % self.selectedRemote
        self.remoteBranches = [b[len(prefix):] for b in self.repo.remote_branches.keys() if b.startswith(prefix)]
        self.remoteBranches.sort()
        
        self.branchChooser.Clear()
        for branch in self.remoteBranches:
            self.branchChooser.Append(branch)
        self.branchChooser.Append('New branch...')
        self.branchChooser.Select(0)
        self.OnBranchChosen()

    def OnBranchChosen(self, e=None):
        branchIndex = self.branchChooser.GetSelection()
        if branchIndex == len(self.remoteBranches):
            self.branchEntry.Show()
            self.selectedBranch = self.branchEntry.GetValue()
        else:
            self.branchEntry.Hide()
            self.selectedBranch = self.remoteBranches[branchIndex]

        self.dialog.Layout()
        self.dialog.Fit()
    
    def OnBranchText(self, e):
        self.selectedBranch = self.branchEntry.GetValue()
    
    def OnForcePush(self, e):
        self.forcePush = self.forcePushCheckbox.GetValue()
    
    def HideWarning(self):
        self.warningLabel.Hide()
        self.detailsButton.Hide()

class PushProgressDialog(object):
    def __init__(self, parent, id, repo, remote, commit, remoteBranch, forcePush):
        self.parent = parent
        self.repo = repo
        self.remote = remote
        self.commit = commit
        self.remoteBranch = remoteBranch
        self.forcePush = forcePush
        
        # Setup dialog
        self.dialog = LoadDialog(parent, 'PushProgressDialog')
        self.dialog.SetMinSize((350, -1))
        self.dialog.SetTitle('Pushing to %s...' % remote)
        
        # Widgets
        self.progressLabel = GetWidget(self.dialog, 'progressLabel')
        self.progressBar = GetWidget(self.dialog, 'progressBar')
        SetupEvents(self.dialog, [
            ('cancelButton', wx.EVT_BUTTON, self.OnCancel)
        ])
    
    def ShowModal(self):
        self.progressLabel.SetLabel('Connecting to remote repository...')
        self.progressBar.Pulse()
        self.dialog.Fit()
        
        self.pushThread = self.repo.push_bg(self.remote, self.commit, self.remoteBranch, self.forcePush, self.ProgressCallback)
        return self.dialog.ShowModal()
    
    def ProgressCallback(self, event, param):
        if event == TRANSFER_COMPRESSING:
            wx.CallAfter(self.progressLabel.SetLabel, "Compressing objects...")
            wx.CallAfter(self.progressBar.SetValue, param)
        elif event == TRANSFER_WRITING:
            wx.CallAfter(self.progressLabel.SetLabel, "Writing objects...")
            wx.CallAfter(self.progressBar.SetValue, param)
        elif event == TRANSFER_ENDED:
            wx.CallAfter(self.OnPushEnded, param)
    
    def OnPushEnded(self, error):
        if error:
            wx.MessageBox(safe_unicode(error), 'Error', style=wx.OK|wx.ICON_ERROR)
            self.dialog.EndModal(0)
        else:
            self.dialog.EndModal(1)
    
    def OnCancel(self, e):
        self.pushThread.abort()
        self.dialog.EndModal(0)

########NEW FILE########
__FILENAME__ = run
#!/usr/bin/env python
# -*- coding: utf-8

import sys
import os
import os.path
import wx

from git import Repository
from MainWindow import *
from PasswordDialog import *
from HiddenWindow import *

class StupidGitApp(wx.PySimpleApp):
    def InitApp(self):
        self.SetAppName('StupidGit')
        wx.TheApp = self
        self.app_windows = []
        if sys.platform == 'darwin':
            self.hiddenWindow = HiddenWindow()
            self.SetExitOnFrameDelete(False)
            wx.App_SetMacAboutMenuItemId(xrc.XRCID('aboutMenuItem'))
            wx.App_SetMacExitMenuItemId(xrc.XRCID('quitMenuItem'))
        
    def OpenRepo(self, repo=None):
        # Find the first empty window (if exists)
        win = None
        for app_window in self.app_windows:
            if not app_window.mainRepo:
                win = app_window
                break
        
        if win:
            # Open repository in existing empty window
            win.SetMainRepo(repo)
        else:
            # Create a new window
            win = MainWindow(repo)
            win.Show(True)
    
    def OnWindowCreated(self, win):
        self.app_windows.append(win)
    
    def OnWindowClosed(self, win):
        self.app_windows.remove(win)
        if len(self.app_windows) == 0 and sys.platform == 'darwin':
            self.hiddenWindow.ShowMenu()
    
    def ExitApp(self):
        while self.app_windows:
            self.app_windows[0].frame.Close(True)
        self.ExitMainLoop()
    
    def MacOpenFile(self, filename):
        try:
            repo = Repository(filename)
            self.OpenRepo(repo)
        except GitError:
            pass

def main_normal():
    # Parse arguments
    repodir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()

    # Show main window
    try:
        repo = Repository(repodir)
    except GitError:
        repo = None
    
    app = StupidGitApp()
    app.InitApp()
    app.OpenRepo(repo)
    app.MainLoop()

def main_askpass():
    app = wx.PySimpleApp()

    askpass = PasswordDialog(None, -1, ' '.join(sys.argv[1:]))
    askpass.ShowModal()

    if askpass.password:
        print askpass.password
        sys.exit(0)
    else:
        sys.exit(1)

def main():
    if 'askpass' in sys.argv[0]:
        main_askpass()
    else:
        main_normal()

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = SwitchWizard
import sys
import wx
import git
import platformspec
import os
from Dialogs import CommitListDialog, UncommittedFilesDialog

from util import *

SWMODE_EXISTING_BRANCH  = 'Checkout branch...'
SWMODE_NEW_BRANCH       = 'Checkout as new branch...'
SWMODE_DETACHED_HEAD    = 'Checkout as detached HEAD'
SWMODE_MOVE_BRANCH      = 'Move branch here...'

WORKDIR_CHECKOUT        = 0
WORKDIR_KEEP            = 1

UNCOMMITTED_SAFE_MODE   = 0
UNCOMMITTED_MERGE       = 1
UNCOMMITTED_DISCARD     = 2

SUBMODULE_MOVE_BRANCH   = 0
SUBMODULE_DETACHED_HEAD = 1
SUBMODULE_NEW_BRANCH    = 2

class SwitchWizard(wx.Dialog):
    def __init__(self, parent, id, repo, targetCommit):
        wx.Dialog.__init__(self, parent, id)

        self.repo = repo
        self.targetCommit = targetCommit

        # Basic layout
        self.SetTitle('Switch to version...')
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(sizer, 1, wx.ALL, 5)

        choiceTopPadding = 4 if sys.platform == 'darwin' else 0

        # Detect capabilities
        self.targetBranches = [ branch for (branch,sha1) in self.repo.branches.iteritems() if sha1 == targetCommit.sha1 ]
        self.targetBranches.sort()

        self.allBranches = [ branch for (branch,sha1) in self.repo.branches.iteritems() ]

        if self.targetBranches:
            self.switchModes = [SWMODE_EXISTING_BRANCH, SWMODE_NEW_BRANCH, SWMODE_DETACHED_HEAD, SWMODE_MOVE_BRANCH]
            branchChoices = self.targetBranches
        elif self.allBranches:
            self.switchModes = [SWMODE_NEW_BRANCH, SWMODE_DETACHED_HEAD, SWMODE_MOVE_BRANCH]
            branchChoices = self.allBranches
        else:
            self.switchModes = [SWMODE_NEW_BRANCH, SWMODE_DETACHED_HEAD]
            branchChoices = []

        self.hasUncommittedChanges = (len(self.repo.get_unified_status()) > 0)

        self.hasSubmodules = (len(self.repo.submodules) > 0)

        # Default values
        self.switchMode = self.switchModes[0]
        self.workdirMode = WORKDIR_CHECKOUT
        self.uncommittedMode = UNCOMMITTED_SAFE_MODE
        self.submoduleSwitch = False
        self.submoduleMode = SUBMODULE_MOVE_BRANCH
        self.newBranchName = ''
        self.submoduleBranchName = ''
        if self.switchMode == SWMODE_EXISTING_BRANCH:
            self.targetBranch = self.targetBranches[0]
        else:
            self.targetBranch = ''
        self.error = None
        self.submoduleWarnings = {}

        # -------------------- Switch mode ---------------------
        # Switch mode
        self.swmodeSizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.swmodeSizer, 0, wx.EXPAND | wx.ALL, 5)

        self.swmodeSizer.Add(wx.StaticText(self, -1, 'Switch mode:'), 0, wx.ALIGN_CENTRE_VERTICAL | wx.RIGHT, 5)
        self.swmodeChoices = wx.Choice(self, -1, choices=self.switchModes)
        self.swmodeSizer.Add(self.swmodeChoices, 0, wx.ALIGN_CENTRE_VERTICAL | wx.TOP | wx.RIGHT, choiceTopPadding)
        self.swmodeChoices.Select(0)
        self.Bind(wx.EVT_CHOICE, self.OnSwitchModeChosen, self.swmodeChoices)

        # Branch selector
        self.branchChoices = wx.Choice(self, -1, choices=branchChoices)
        self.swmodeSizer.Add(self.branchChoices, 1, wx.ALIGN_CENTRE_VERTICAL | wx.TOP | wx.RIGHT, choiceTopPadding)
        if branchChoices:
            self.branchChoices.Select(0)
        self.branchChoices.Bind(wx.EVT_CHOICE, self.OnBranchChosen)
        self.branchChoices.Show(self.switchModes[0] != SWMODE_NEW_BRANCH)

        # New branch text box
        self.newBranchTxt = wx.TextCtrl(self, -1)
        self.newBranchTxt.Bind(wx.EVT_TEXT, self.Validate)
        self.swmodeSizer.Add(self.newBranchTxt, 1, wx.ALIGN_CENTRE_VERTICAL | wx.LEFT | wx.RIGHT, 5)
        self.newBranchTxt.Show(self.switchModes[0] == SWMODE_NEW_BRANCH)

        # ------------------ Working directory ------------------
        # Static box
        self.workdirBox = wx.StaticBox(self, -1, 'Working directory:')
        self.workdirSizer = wx.StaticBoxSizer(self.workdirBox, wx.VERTICAL)
        sizer.Add(self.workdirSizer, 0, wx.EXPAND | wx.ALL, 5)

        # Radio buttons
        btn = wx.RadioButton(self, -1, 'Switch file contents to new version', style=wx.RB_GROUP)
        btn.SetValue(True)
        btn.Bind(wx.EVT_RADIOBUTTON, lambda e:self.OnWorkdirMode(WORKDIR_CHECKOUT))
        self.workdirSizer.Add(btn, 0, wx.ALL, 5)

        btn = wx.RadioButton(self, -1, 'Keep files unchanged')
        btn.Bind(wx.EVT_RADIOBUTTON, lambda e:self.OnWorkdirMode(WORKDIR_KEEP))
        self.workdirSizer.Add(btn, 0, wx.ALL, 5)

        # ------------------ Uncommitted changes -----------------
        if self.hasUncommittedChanges:
            self.uncommittedBox = wx.StaticBox(self, -1, 'Uncommitted changes:')
            self.uncommittedSizer = wx.StaticBoxSizer(self.uncommittedBox, wx.VERTICAL)
            sizer.Add(self.uncommittedSizer, 0, wx.EXPAND | wx.ALL, 5)

            # Radio buttons
            self.uncommittedButtons = []

            btn = wx.RadioButton(self, -1, 'Switch only if these files need not to be modified', style=wx.RB_GROUP)
            btn.SetValue(True)
            btn.Bind(wx.EVT_RADIOBUTTON, lambda e:self.OnUncommittedMode(UNCOMMITTED_SAFE_MODE))
            self.uncommittedButtons.append(btn)
            self.uncommittedSizer.Add(btn, 0, wx.ALL, 5)

            btn = wx.RadioButton(self, -1, 'Merge uncommitted changes into new version')
            btn.Bind(wx.EVT_RADIOBUTTON, lambda e:self.OnUncommittedMode(UNCOMMITTED_MERGE))
            self.uncommittedButtons.append(btn)
            self.uncommittedSizer.Add(btn, 0, wx.ALL, 5)

            btn = wx.RadioButton(self, -1, 'Discard uncommitted changes')
            btn.Bind(wx.EVT_RADIOBUTTON, lambda e:self.OnUncommittedMode(UNCOMMITTED_DISCARD))
            self.uncommittedButtons.append(btn)
            self.uncommittedSizer.Add(btn, 0, wx.ALL, 5)

            btn = wx.Button(self, -1, 'Review uncommitted changes')
            btn.Bind(wx.EVT_BUTTON, self.OnReviewUncommittedChanges)
            self.uncommittedSizer.Add(btn, 0, wx.ALL, 5)

        # ----------------------- Submodules ----------------------
        if self.hasSubmodules:
            self.submoduleBox = wx.StaticBox(self, -1, 'Submodules:')
            self.submoduleSizer = wx.StaticBoxSizer(self.submoduleBox, wx.VERTICAL)
            sizer.Add(self.submoduleSizer, 0, wx.EXPAND | wx.ALL, 5)

            # Submodule checkbox
            self.submoduleChk = wx.CheckBox(self, -1, 'Switch submodules to referenced version')
            self.submoduleChk.SetValue(False)
            self.submoduleChk.Bind(wx.EVT_CHECKBOX, self.OnSubmoduleSwitch)
            self.submoduleSizer.Add(self.submoduleChk, 0, wx.ALL, 5)

            # Radio buttons
            self.submoduleModeButtons = []

            btn = wx.RadioButton(self, -1, 'Move currently selected branches (only if no commits will be lost)', style=wx.RB_GROUP)
            btn.SetValue(1)
            btn.Enable(False)
            btn.Bind(wx.EVT_RADIOBUTTON, lambda e:self.OnSubmoduleMode(SUBMODULE_MOVE_BRANCH))
            self.submoduleSizer.Add(btn, 0, wx.ALL, 5)
            self.submoduleModeButtons.append(btn)

            btn = wx.RadioButton(self, -1, 'Switch to detached HEAD')
            btn.Bind(wx.EVT_RADIOBUTTON, lambda e:self.OnSubmoduleMode(SUBMODULE_DETACHED_HEAD))
            btn.Enable(False)
            self.submoduleSizer.Add(btn, 0, wx.ALL, 5)
            self.submoduleModeButtons.append(btn)

            s = wx.BoxSizer(wx.HORIZONTAL)
            self.submoduleSizer.Add(s, 0, wx.ALL, 5)

            btn = wx.RadioButton(self, -1, 'Switch to new branch:')
            btn.Bind(wx.EVT_RADIOBUTTON, lambda e:self.OnSubmoduleMode(SUBMODULE_NEW_BRANCH))
            btn.Enable(False)
            s.Add(btn, 0)
            self.submoduleModeButtons.append(btn)

            # New branch text field
            self.submoduleBranchTxt = wx.TextCtrl(self, -1)
            self.submoduleBranchTxt.Bind(wx.EVT_TEXT, self.Validate)
            s.Add(self.submoduleBranchTxt, 0, wx.LEFT, 7)
            self.submoduleBranchTxt.Enable(False)

        # Status message
        self.statusSizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.statusSizer, 0, wx.EXPAND | wx.TOP, 15)

        self.statusMsg = wx.StaticText(self, -1, '')
        self.statusSizer.Add(self.statusMsg, 1, wx.LEFT, 5)

        self.statusButton = wx.Button(self, -1, 'Details')
        self.statusButton.Bind(wx.EVT_BUTTON, self.OnDetailsButton)
        self.statusSizer.Add(self.statusButton, 0, wx.LEFT | wx.RIGHT, 5)

        # Finish buttons
        s = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(s, 0, wx.TOP | wx.BOTTOM | wx.ALIGN_RIGHT, 15)

        self.okButton = wx.Button(self, -1, 'OK')
        self.okButton.Bind(wx.EVT_BUTTON, self.OnOkClicked)
        s.Add(self.okButton, 0, wx.LEFT | wx.RIGHT, 5)

        self.cancelButton = wx.Button(self, -1, 'Cancel')
        self.cancelButton.Bind(wx.EVT_BUTTON, self.OnCancelClicked)
        s.Add(self.cancelButton, 0, wx.LEFT | wx.RIGHT, 5)

        self.Validate()

        # Resize window
        self.Fit()
        self.Layout()
        w,h = self.GetSize()
        self.SetSize((max(450,w),h))

    def Validate(self, e=None):
        isValid = True

        # If we are on a detached head, we may always lose commits
        self.lostCommits = []
        if not self.repo.current_branch:
            self.lostCommits = self.repo.get_lost_commits('HEAD', self.targetCommit.sha1)

        # Validate branch name
        if self.switchMode == SWMODE_NEW_BRANCH:
            self.newBranchName = self.newBranchTxt.GetValue().strip()
            if not self.newBranchName:
                isValid = False
                self.statusMsg.SetLabel('Enter the name of the new branch!')
            elif self.newBranchName in self.repo.branches.keys():
                isValid = False
                self.statusMsg.SetLabel("Branch '%s' already exists!" % self.newBranchName)

        # Check lost commits of moved branch
        elif self.switchMode == SWMODE_MOVE_BRANCH:
            lostCommits = self.repo.get_lost_commits('refs/heads/' + self.targetBranch, self.targetCommit.sha1)
            for c in lostCommits:
                if c not in self.lostCommits:
                    self.lostCommits.append(c)

        # Check submodule branch name
        if isValid and self.submoduleMode == SUBMODULE_NEW_BRANCH:
            self.submoduleBranchName = self.submoduleBranchTxt.GetValue().strip()
            if not self.submoduleBranchName:
                isValid = False
                self.statusMsg.SetLabel('Enter the name of the new submodule branch!')

        # Enable / disable controls according to validity
        if isValid:
            self.okButton.Enable(1)

            # Show warning about lost commits
            if self.lostCommits:
                if len(self.lostCommits) == 1:
                    msg = 'WARNING: You will permanently lose a commit!'
                else:
                    msg = 'WARNING: You will permanently lose %d commits!' % len(self.lostCommits)
                self.statusMsg.SetLabel(msg)
                self.statusButton.Show(1)
            else:
                self.statusMsg.SetLabel('')
                self.statusButton.Show(0)
        else:
            self.okButton.Enable(0)
            self.statusButton.Show(0)

        # Refresh layout
        self.statusSizer.Layout()

    def OnSwitchModeChosen(self, e):
        self.switchMode = e.GetString()

        if self.switchMode == SWMODE_EXISTING_BRANCH:
            self.branchChoices.Show(1)
            self.newBranchTxt.Show(0)

            self.targetBranch = self.targetBranches[0]
            self.branchChoices.Clear()
            for branch in self.targetBranches:
                self.branchChoices.Append(branch)
            self.branchChoices.Select(0)

        elif self.switchMode == SWMODE_NEW_BRANCH:
            self.branchChoices.Show(0)
            self.newBranchTxt.Show(1)

            self.newBranchTxt.SetValue('')

        elif self.switchMode == SWMODE_DETACHED_HEAD:
            self.branchChoices.Show(0)
            self.newBranchTxt.Show(0)

        elif self.switchMode == SWMODE_MOVE_BRANCH:
            self.branchChoices.Show(1)
            self.newBranchTxt.Show(0)

            # Select current branch by default
            if self.repo.current_branch:
                branchIndex = self.allBranches.index(self.repo.current_branch)
            else:
                branchIndex = 0

            self.targetBranch = self.allBranches[branchIndex]
            self.branchChoices.Clear()
            for branch in self.allBranches:
                self.branchChoices.Append(branch)
            self.branchChoices.Select(branchIndex)

        self.swmodeSizer.RecalcSizes()
        self.Validate()

    def OnBranchChosen(self, e):
        if self.switchMode in [SWMODE_EXISTING_BRANCH, SWMODE_MOVE_BRANCH]:
            self.targetBranch = e.GetString()
        else:
            self.targetBranch = ''

        self.Validate()

    def OnWorkdirMode(self, workdirMode):
        self.workdirMode = workdirMode

        if self.hasUncommittedChanges:
            uncommittedModeEnabled = (workdirMode == WORKDIR_CHECKOUT)
            for btn in self.uncommittedButtons:
                btn.Enable(uncommittedModeEnabled)

        self.Validate()

    def OnUncommittedMode(self, uncommittedMode):
        self.uncommittedMode = uncommittedMode
        self.Validate()

    def OnReviewUncommittedChanges(self, e):
        dialog = UncommittedFilesDialog(self, -1, self.repo)
        dialog.SetTitle('Uncommitted changes')
        dialog.SetMessage('The following changes are not committed:')
        dialog.ShowModal()

    def OnDetailsButton(self, e):
        if self.repo.current_branch == None:
            if self.switchMode == SWMODE_MOVE_BRANCH:
                message = 'By moving a detached HEAD and/or branch \'%s\' to a different position ' % self.targetBranch
            else:
                message = 'By moving a detached HEAD to a different position '
        else:
            message = 'By moving branch \'%s\' to a different position ' % self.targetBranch

        message += 'some of the commits will not be referenced by any ' + \
                   'branch, tag or remote branch. They will disappear from the ' + \
                   'history graph and will be permanently lost.\n\n' + \
                   'These commits are:'

        dialog = CommitListDialog(self, -1, self.repo, self.lostCommits)
        dialog.SetTitle('Review commits to be lost')
        dialog.SetMessage(message)
        dialog.ShowModal()

    def OnSubmoduleSwitch(self, e):
        self.submoduleSwitch = self.submoduleChk.GetValue()

        for btn in self.submoduleModeButtons:
            btn.Enable(self.submoduleSwitch)

        if self.submoduleSwitch:
            self.submoduleBranchTxt.Enable(self.submoduleMode == SUBMODULE_NEW_BRANCH)
        else:
            self.submoduleBranchTxt.Enable(False)

        self.Validate()

    def OnSubmoduleMode(self, submoduleMode):
        self.submoduleMode = submoduleMode
        self.submoduleBranchTxt.Enable(submoduleMode == SUBMODULE_NEW_BRANCH)
        self.Validate()

    def OnOkClicked(self, e):
        # Update references
        self.repo.load_refs()

        try:
            # Switch to new version (as detached HEAD)
            if self.workdirMode == WORKDIR_KEEP:
                self.repo.run_cmd(['update-ref', '--no-deref', 'HEAD', self.targetCommit.sha1], raise_error=True)
            elif self.uncommittedMode == UNCOMMITTED_SAFE_MODE:
                self.repo.run_cmd(['checkout', self.targetCommit.sha1], raise_error=True)
            elif self.uncommittedMode == UNCOMMITTED_MERGE:
                self.repo.run_cmd(['checkout', '-m', self.targetCommit.sha1], raise_error=True)
            elif self.uncommittedMode == UNCOMMITTED_DISCARD:
                self.repo.run_cmd(['reset', '--hard'], raise_error=True)
                self.repo.run_cmd(['clean', '-f'], raise_error=True)

            # Checkout branch
            branch = None
            if self.switchMode in [SWMODE_EXISTING_BRANCH, SWMODE_MOVE_BRANCH]:
                branch = self.targetBranch
            elif self.switchMode == SWMODE_NEW_BRANCH:
                branch = self.newBranchName
            if branch:
                if self.switchMode != SWMODE_EXISTING_BRANCH:
                    self.repo.run_cmd(['update-ref', 'refs/heads/%s' % branch, self.targetCommit.sha1], raise_error=True)
                self.repo.update_head('ref: refs/heads/%s' % branch)

        except git.GitError, e:
            self.error = str(e).partition('\n')[2].strip()
            if not self.error:
                self.error = str(e)
            self.EndModal(1)
            return

        # Update submodules
        if self.submoduleSwitch:
            self.repo.load_refs()

            for submodule in self.repo.submodules:
                submodule.load_refs()
                submodule.get_log(['--topo-order', '--all']) # Update commit pool

                # Check existence of referenced commit
                if submodule.main_ref not in git.commit_pool:
                    self.submoduleWarnings[submodule.name] = 'Referenced version cannot be found'
                    continue
                commit = git.commit_pool[submodule.main_ref]
                
                # Check lost commits
                lostCommits = submodule.get_lost_commits('HEAD', commit.sha1)
                if self.submoduleMode == SUBMODULE_MOVE_BRANCH and submodule.current_branch:
                    lostCommits += submodule.get_lost_commits('refs/heads/%s' % submodule.current_branch, commit.sha1)
                if lostCommits:
                    self.submoduleWarnings[submodule.name] = 'Switching to new version would result in lost commits'
                    continue

                # Try to checkout (in safe mode)
                try:
                    # Reset submodule so that it won't be unmerged
                    self.repo.run_cmd(['reset', submodule.name])

                    if self.submoduleMode == SUBMODULE_DETACHED_HEAD:
                        submodule.run_cmd(['checkout', commit.sha1], raise_error=True)
                    elif self.submoduleMode == SUBMODULE_NEW_BRANCH:
                        if self.submoduleBranchName in submodule.branches:
                            self.submoduleWarnings[submodule.name] = "Branch '%s' already exists!" % self.submoduleBranchName
                            continue
                        submodule.run_cmd(['branch', self.submoduleBranchName, commit.sha1], raise_error=True)
                        submodule.run_cmd(['checkout', self.submoduleBranchName], raise_error=True)
                    elif self.submoduleMode == SUBMODULE_MOVE_BRANCH:
                        submodule.run_cmd(['checkout', commit.sha1], raise_error=True)
                        if submodule.current_branch:
                            submodule.run_cmd(['update-ref', 'refs/heads/%s' % submodule.current_branch, commit.sha1], raise_error=True)
                            submodule.run_cmd(['checkout', submodule.current_branch], raise_error=True)
                except git.GitError, e:
                    error_line = str(e).partition('\n')[2].strip()
                    if not error_line:
                        error_line = e
                    self.submoduleWarnings[submodule.name] = error_line

        self.EndModal(1)

    def OnCancelClicked(self, e):
        self.EndModal(0)

    def RunWizard(self):
        return self.ShowModal()


########NEW FILE########
__FILENAME__ = util
import locale
import sys
import os
import os.path
import subprocess
if sys.platform == 'win32':
    import ctypes

def safe_unicode(s):
    '''Creates unicode object from string s.
    It tries to decode string as UTF-8, fallbacks to current locale
    or ISO-8859-1 if both decode attemps fail'''

    if type(s) == unicode:
        return s
    elif isinstance(s, Exception):
        s = str(s)
    
    try:
        return s.decode('UTF-8')
    except UnicodeDecodeError:
        pass

    try:
        lang,encoding = locale.getdefaultlocale()
    except ValueError:
        lang,encoding = 'C','UTF-8'

    if encoding != 'UTF-8':
        try:
            return s.decode(encoding)
        except UnicodeDecodeError:
            pass

    return s.decode('ISO-8859-1')

def utf8_str(s):
    s = safe_unicode(s)
    return s.encode('UTF-8')

def invert_hash(h):
    ih = {}

    for key,value in h.iteritems():
        if value not in ih:
            ih[value] = []
        ih[value].append(key)

    return ih

def find_binary(locations):
    searchpath_sep = ';' if sys.platform == 'win32' else ':'
    searchpaths = os.environ['PATH'].split(searchpath_sep)

    for location in locations:
        if '{PATH}' in location:
            for searchpath in searchpaths:
                s = location.replace('{PATH}', searchpath)
                if os.path.isfile(s) and os.access(s, os.X_OK):
                    yield s
        elif os.path.isfile(location) and os.access(location, os.X_OK):
            yield location

def is_binary_file(file):
    # Returns True if the file cannot be decoded as UTF-8
    # and > 20% of the file is binary character

    # Read file
    try:
        f = open(file)
        buf = f.read()
        f.close()
    except OSError:
        return False

    # Decode as UTF-8
    try:
        ubuf = unicode(buf, 'utf-8')
        return False
    except UnicodeDecodeError:
        pass

    # Check number of binary characters
    treshold = len(buf) / 5
    binary_chars = 0
    for c in buf:
        oc = ord(c)
        if oc > 0x7f or (oc < 0x1f and oc != '\r' and oc != '\n'):
            binary_chars += 1
            if binary_chars > treshold:
                return True

    return False

PROCESS_TERMINATE = 1
def kill_subprocess(process):
    if sys.platform == 'win32':
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, process.pid)
        ctypes.windll.kernel32.TerminateProcess(handle, -1)
        ctypes.windll.kernel32.CloseHandle(handle)
    else:
        os.kill(process.pid, 9)

CREATE_NO_WINDOW = 0x08000000
def Popen(cmd, **args):
    # Create a subprocess that does not open a new console window
    if sys.platform == 'win32':
        process = subprocess.Popen(cmd, creationflags = CREATE_NO_WINDOW, **args)
    else:
        process = subprocess.Popen(cmd, **args)

    # Emulate kill() for Python 2.5
    if 'kill' not in dir(process):
        process.kill = lambda: kill_subprocess(process)

    return process


########NEW FILE########
__FILENAME__ = Wizard
import wx

BTN_NEXT     = "Next >"
BTN_PREV     = "< Previous"
BTN_CONTINUE = "Continue >"
BTN_CANCEL   = "Cancel"
BTN_FINISH   = "Finish"

class Wizard(wx.Dialog):
    def __init__(self, parent, id):
        wx.Dialog.__init__(self, parent, id, size=wx.Size(600,400))

        # Layout
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        # Page container
        self.pageSizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.pageSizer, 1, wx.EXPAND | wx.ALL, 5)
        self.currentPage = None

        # Button container
        self.buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(self.buttonSizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)
        self.buttons = []

    def SetPage(self, page):
        # Remove old page from layout
        if self.currentPage:
            self.pageSizer.Detach(self.currentPage)
            self.currentPage.Hide()

        # Add new page to layout
        self.currentPage = page
        self.currentPage.Show()
        self.pageSizer.Add(self.currentPage, 1, wx.EXPAND)
        self.currentPage.sizer.Layout()
        self.pageSizer.Layout()
        self.sizer.Layout()
        
        # Show buttons
        self.SetButtons(page.buttons)

        # Replace title
        self.SetTitle(page.caption)

    def SetButtons(self, buttonLabels):
        for button in self.buttons:
            self.buttonSizer.Detach(button)
            button.Destroy()

        self.buttons = [ wx.Button(self, -1, label) for label in buttonLabels ]
        for button in self.buttons:
            self.Bind(wx.EVT_BUTTON, self._onButton, button)
            self.buttonSizer.Add(button, 0, wx.LEFT, 5)

        self.sizer.Layout()

    def _onButton(self, e):
        self.OnButtonClicked(e.GetEventObject().GetLabel())

    def RunWizard(self):
        self.OnStart()
        return self.ShowModal()

    def EndWizard(self, retval):
        self.EndModal(retval)

    # Abstract functions
    def OnStart(self):
        pass

    def OnButtonClicked(self, button):
        pass

    # Helper functions to create pages
    def CreatePage(self, caption, buttons=[]):
        page = wx.Panel(self, -1)
        page.caption = caption
        page.buttons = buttons
        page.sizer = wx.BoxSizer(wx.VERTICAL)
        page.SetSizer(page.sizer)
        page.Hide()

        return page

    def CreateWarningPage(self, caption, message, buttons=[]):
        page = self.CreatePage(caption, buttons)

        captionFont = wx.Font(16, wx.DEFAULT, wx.NORMAL, wx.BOLD) 
        page.captionText = wx.StaticText(page, -1, caption)
        page.captionText.SetFont(captionFont)

        page.text = wx.StaticText(page, -1, message)

        page.sizer.Add(page.captionText, 0, wx.ALL, 10)
        page.sizer.Add(page.text, 1, wx.EXPAND | wx.ALL, 10)
        
        return page


########NEW FILE########
__FILENAME__ = wxutil
import os
import os.path
import wx
from wx import xrc

_resource_dir = None
def resource_dir():
    global _resource_dir
    if 'STUPIDGIT_RESOURCES' in os.environ:
        _resource_dir = os.environ['STUPIDGIT_RESOURCES']
    elif not _resource_dir:
        if os.path.commonprefix([__file__, '/usr/lib/pymodules']) == '/usr/lib/pymodules':
            _resource_dir = '/usr/share/stupidgit'
        else:
            _resource_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'resources'))

    return _resource_dir

_xrc_resource = None
def _xrc():
    global _xrc_resource
    if not _xrc_resource:
        _xrc_resource = xrc.XmlResource(os.path.join(resource_dir(), 'stupidgit.xrc'))

    return _xrc_resource

def LoadFrame(parent, frameName):
    return _xrc().LoadFrame(parent, frameName)

def LoadDialog(parent, frameName):
    return _xrc().LoadDialog(parent, frameName)

def SetupEvents(parent, eventHandlers):
    for name, event, handler in eventHandlers:
        if name:
            parent.Bind(event, handler, id=xrc.XRCID(name))
        else:
            parent.Bind(event, handler)

def GetWidget(parent, name):
    return xrc.XRCCTRL(parent, name)


########NEW FILE########
