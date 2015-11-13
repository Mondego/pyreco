__FILENAME__ = convert
'''
This utility script converts (row, col, value) records like this:

    2,6,9
    2,7,23
    2,8,74
    ...
    6,20,76
    6,21,27
    6,22,0

Into a tabular format like this:

,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22
2,9,23,74,225,351,434,513,666,710,890,776,610,435,166,100,46,1
3,12,29,53,166,250,369,370,428,549,625,618,516,386,179,101,51,5
4,9,30,79,214,350,460,478,568,677,743,700,448,473,207,138,42,2
5,9,16,84,171,294,342,435,470,552,594,642,518,350,182,95,54,2
6,13,27,93,224,402,568,693,560,527,374,364,223,139,89,76,27,0

The tabular format CSV can then be used with punchcard.py
'''

import csv

def process(path):
    with open(path, 'rb') as fp:
        reader = csv.reader(fp)
        csv_rows = list(reader)
    rows = set()
    cols = set()
    lookup = {}
    int_rows = all(x[0].isdigit() for x in csv_rows[1:])
    int_cols = all(x[1].isdigit() for x in csv_rows[1:])
    for row, col, value in csv_rows[1:]:
        if int_rows:
            row = int(row)
        if int_cols:
            col = int(col)
        rows.add(row)
        cols.add(col)
        lookup[(row, col)] = value
    rows = sorted(rows)
    cols = sorted(cols)
    result = [[''] + cols]
    for row in rows:
        data = [lookup.get((row, col), 0) for col in cols]
        result.append([row] + data)
    with open(path, 'wb') as fp:
        writer = csv.writer(fp)
        writer.writerows(result)

if __name__ == '__main__':
    import sys
    process(sys.argv[1])

########NEW FILE########
__FILENAME__ = punchcard
from math import pi, sin
import csv
import cairo
import pango
import pangocairo
import sizers

DEFAULTS = {
    'padding': 12,
    'cell_padding': 4,
    'min_size': 4,
    'max_size': 32,
    'min_color': 0.8,
    'max_color': 0.0,
    'font': 'Helvetica',
    'font_size': 14,
    'font_bold': False,
    'title': None,
    'title_font': 'Helvetica',
    'title_font_size': 20,
    'title_font_bold': True,
    'diagonal_column_labels': False,
}

class Text(object):
    def __init__(self, dc=None):
        self.dc = dc or cairo.Context(
            cairo.ImageSurface(cairo.FORMAT_RGB24, 1, 1))
        self.pc = pangocairo.CairoContext(self.dc)
        self.layout = self.pc.create_layout()
    def set_font(self, name, size, bold):
        weight = ' bold ' if bold else ' '
        fd = pango.FontDescription('%s%s%d' % (name, weight, size))
        self.layout.set_font_description(fd)
    def measure(self, text):
        self.layout.set_text(str(text))
        return self.layout.get_pixel_size()
    def render(self, text):
        self.layout.set_text(str(text))
        self.pc.update_layout(self.layout)
        self.pc.show_layout(self.layout)

class ColLabels(sizers.Box):
    def __init__(self, model):
        super(ColLabels, self).__init__()
        self.model = model
    def get_min_size(self):
        if self.model.col_labels is None:
            return (0, 0)
        text = Text()
        text.set_font(
            self.model.font, self.model.font_size, self.model.font_bold)
        width = self.model.width
        height = 0
        for i, col in enumerate(self.model.col_labels):
            tw, th = text.measure(col)
            if self.model.diagonal_column_labels:
                x = i * self.model.cell_size + th / 2
                w = (tw + th / 2) * sin(pi / 4)
                width = max(width, x + w)
                height = max(height, w)
            else:
                height = max(height, tw)
        return (width, height)
    def render(self, dc):
        if self.model.col_labels is None:
            return
        dc.set_source_rgb(0, 0, 0)
        text = Text(dc)
        text.set_font(
            self.model.font, self.model.font_size, self.model.font_bold)
        for i, col in enumerate(self.model.col_labels):
            tw, th = text.measure(col)
            x = self.x + i * self.model.cell_size + th / 2
            y = self.bottom
            dc.save()
            if self.model.diagonal_column_labels:
                dc.translate(x, y - th * sin(pi / 4) / 2)
                dc.rotate(-pi / 4)
            else:
                dc.translate(x, y)
                dc.rotate(-pi / 2)
            dc.move_to(0, 0)
            text.render(col)
            dc.restore()

class RowLabels(sizers.Box):
    def __init__(self, model):
        super(RowLabels, self).__init__()
        self.model = model
    def get_min_size(self):
        if self.model.row_labels is None:
            return (0, 0)
        text = Text()
        text.set_font(
            self.model.font, self.model.font_size, self.model.font_bold)
        width = max(text.measure(x)[0] for x in self.model.row_labels)
        height = self.model.height
        return (width, height)
    def render(self, dc):
        if self.model.row_labels is None:
            return
        dc.set_source_rgb(0, 0, 0)
        text = Text(dc)
        text.set_font(
            self.model.font, self.model.font_size, self.model.font_bold)
        for i, row in enumerate(self.model.row_labels):
            tw, th = text.measure(row)
            x = self.right - tw
            y = self.y + i * self.model.cell_size + th / 2
            dc.move_to(x, y)
            text.render(row)

class Chart(sizers.Box):
    def __init__(self, model):
        super(Chart, self).__init__()
        self.model = model
    def get_min_size(self):
        return (self.model.width, self.model.height)
    def render(self, dc):
        self.render_grid(dc)
        self.render_punches(dc)
    def render_grid(self, dc):
        size = self.model.cell_size
        dc.set_source_rgb(0.5, 0.5, 0.5)
        dc.set_line_width(1)
        for i in range(self.model.cols):
            for j in range(self.model.rows):
                x = self.x + i * size - 0.5
                y = self.y + j * size - 0.5
                dc.rectangle(x, y, size, size)
        dc.stroke()
        dc.set_source_rgb(0, 0, 0)
        dc.set_line_width(3)
        width, height = self.get_min_size()
        dc.rectangle(self.x - 0.5, self.y - 0.5, width, height)
        dc.stroke()
    def render_punches(self, dc):
        data = self.model.data
        size = self.model.cell_size
        lo = min(x for row in data for x in row if x)
        hi = max(x for row in data for x in row if x)
        min_area = pi * (self.model.min_size / 2.0) ** 2
        max_area = pi * (self.model.max_size / 2.0) ** 2
        min_color = self.model.min_color
        max_color = self.model.max_color
        for i in range(self.model.cols):
            for j in range(self.model.rows):
                value = data[j][i]
                if not value:
                    continue
                pct = 1.0 * (value - lo) / (hi - lo)
                # pct = pct ** 0.5
                area = pct * (max_area - min_area) + min_area
                radius = (area / pi) ** 0.5
                color = pct * (max_color - min_color) + min_color
                dc.set_source_rgb(color, color, color)
                x = self.x + i * size + size / 2 - 0.5
                y = self.y + j * size + size / 2 - 0.5
                dc.arc(x, y, radius, 0, 2 * pi)
                dc.fill()

class Title(sizers.Box):
    def __init__(self, model):
        super(Title, self).__init__()
        self.model = model
    def get_min_size(self):
        if self.model.title is None:
            return (0, 0)
        text = Text()
        text.set_font(
            self.model.title_font, self.model.title_font_size,
            self.model.title_font_bold)
        return text.measure(self.model.title)
    def render(self, dc):
        if self.model.title is None:
            return
        dc.set_source_rgb(0, 0, 0)
        text = Text(dc)
        text.set_font(
            self.model.title_font, self.model.title_font_size,
            self.model.title_font_bold)
        tw, th = text.measure(self.model.title)
        x = max(self.x, self.x + self.model.width / 2 - tw / 2)
        y = self.cy - th / 2
        dc.move_to(x, y)
        text.render(self.model.title)

class Model(object):
    def __init__(self, data, row_labels=None, col_labels=None, **kwargs):
        self.data = data
        self.row_labels = row_labels
        self.col_labels = col_labels
        for key, value in DEFAULTS.items():
            value = kwargs.get(key, value)
            setattr(self, key, value)
        self.cell_size = self.max_size + self.cell_padding * 2
        self.rows = len(self.data)
        self.cols = len(self.data[0])
        self.width = self.cols * self.cell_size
        self.height = self.rows * self.cell_size
    def render(self):
        col_labels = ColLabels(self)
        row_labels = RowLabels(self)
        chart = Chart(self)
        title = Title(self)
        grid = sizers.GridSizer(3, 2, self.padding, self.padding)
        grid.add_spacer()
        grid.add(col_labels)
        grid.add(row_labels)
        grid.add(chart)
        grid.add_spacer()
        grid.add(title)
        sizer = sizers.VerticalSizer()
        sizer.add(grid, border=self.padding)
        sizer.fit()
        surface = cairo.ImageSurface(
            cairo.FORMAT_RGB24, int(sizer.width), int(sizer.height))
        dc = cairo.Context(surface)
        dc.set_source_rgb(1, 1, 1)
        dc.paint()
        col_labels.render(dc)
        row_labels.render(dc)
        chart.render(dc)
        title.render(dc)
        return surface

def punchcard(path, data, row_labels, col_labels, **kwargs):
    model = Model(data, row_labels, col_labels, **kwargs)
    surface = model.render()
    surface.write_to_png(path)

def punchcard_from_csv(csv_path, path, **kwargs):
    with open(csv_path, 'rb') as fp:
        reader = csv.reader(fp)
        csv_rows = list(reader)
    row_labels = [x[0] for x in csv_rows[1:]]
    col_labels = csv_rows[0][1:]
    data = []
    for csv_row in csv_rows[1:]:
        row = []
        for value in csv_row[1:]:
            try:
                value = float(value)
            except ValueError:
                value = None
            row.append(value)
        data.append(row)
    punchcard(path, data, row_labels, col_labels, **kwargs)

if __name__ == '__main__':
    import sys
    args = sys.argv[1:]
    if len(args) == 2:
        punchcard_from_csv(args[0], args[1])
    elif len(args) == 3:
        punchcard_from_csv(args[0], args[1], title=args[2])
    else:
        print 'Usage: python punchcard.py input.csv output.png [title]'

########NEW FILE########
__FILENAME__ = sizers
from itertools import product

# Orientation
HORIZONTAL = 1
VERTICAL = 2

# Alignment
NONE = 0
LEFT = 1
RIGHT = 2
TOP = 3
BOTTOM = 4
CENTER = 5

def unpack_border(border):
    try:
        l, t, r, b = border
        return (l, t, r, b)
    except Exception:
        pass
    try:
        x, y = border
        return (x, y, x, y)
    except Exception:
        pass
    n = border
    return (n, n, n, n)

class Target(object):
    def get_min_size(self):
        raise NotImplementedError
    def get_dimensions(self):
        raise NotImplementedError
    def set_dimensions(self, x, y, width, height):
        raise NotImplementedError
    x = l = left = property(lambda self: self.get_dimensions()[0])
    y = t = top = property(lambda self: self.get_dimensions()[1])
    w = width = property(lambda self: self.get_dimensions()[2])
    h = height = property(lambda self: self.get_dimensions()[3])
    r = right = property(lambda self: self.x + self.w)
    b = bottom = property(lambda self: self.y + self.h)
    cx = property(lambda self: self.x + self.w / 2)
    cy = property(lambda self: self.y + self.h / 2)

class Box(Target):
    def __init__(self, width=0, height=0):
        self.min_size = (width, height)
        self.dimensions = (0, 0, width, height)
    def get_min_size(self):
        return self.min_size
    def get_dimensions(self):
        return self.dimensions
    def set_dimensions(self, x, y, width, height):
        self.dimensions = (x, y, width, height)

class SizerItem(object):
    def __init__(self, target, proportion, expand, border, align):
        self.target = target
        self.proportion = proportion
        self.expand = expand
        self.border = unpack_border(border)
        self.align = align
    def get_min_size(self):
        l, t, r, b = self.border
        width, height = self.target.get_min_size()
        width = width + l + r
        height = height + t + b
        return (width, height)
    def get_dimensions(self):
        return self.target.get_dimensions()
    def set_dimensions(self, x, y, width, height):
        l, t, r, b = self.border
        lr, tb = l + r, t + b
        self.target.set_dimensions(x + l, y + t, width - lr, height - tb)

class Sizer(Target):
    def __init__(self):
        self.items = []
        self.dimensions = (0, 0, 0, 0)
    def add(self, target, proportion=0, expand=False, border=0, align=NONE):
        item = SizerItem(target, proportion, expand, border, align)
        self.items.append(item)
    def add_spacer(self, size=0):
        spacer = Box(size, size)
        self.add(spacer)
    def add_stretch_spacer(self, proportion=1):
        spacer = Box()
        self.add(spacer, proportion)
    def get_dimensions(self):
        return self.dimensions
    def set_dimensions(self, x, y, width, height):
        min_width, min_height = self.get_min_size()
        width = max(min_width, width)
        height = max(min_height, height)
        self.dimensions = (x, y, width, height)
        self.layout()
    def fit(self):
        width, height = self.get_min_size()
        self.set_dimensions(0, 0, width, height)
    def get_min_size(self):
        raise NotImplementedError
    def layout(self):
        raise NotImplementedError

class BoxSizer(Sizer):
    def __init__(self, orientation):
        super(BoxSizer, self).__init__()
        self.orientation = orientation
    def get_min_size(self):
        width = 0
        height = 0
        for item in self.items:
            w, h = item.get_min_size()
            if self.orientation == HORIZONTAL:
                width += w
                height = max(height, h)
            else:
                width = max(width, w)
                height += h
        return (width, height)
    def layout(self):
        x, y = self.x, self.y
        width, height = self.width, self.height
        min_width, min_height = self.get_min_size()
        extra_width = max(0, width - min_width)
        extra_height = max(0, height - min_height)
        total_proportions = float(sum(item.proportion for item in self.items))
        if self.orientation == HORIZONTAL:
            for item in self.items:
                w, h = item.get_min_size()
                if item.expand:
                    h = height
                if item.proportion:
                    p = item.proportion / total_proportions
                    w += int(extra_width * p)
                if item.align == CENTER:
                    offset = height / 2 - h / 2
                    item.set_dimensions(x, y + offset, w, h)
                elif item.align == BOTTOM:
                    item.set_dimensions(x, y + height - h, w, h)
                else: # TOP
                    item.set_dimensions(x, y, w, h)
                x += w
        else:
            for item in self.items:
                w, h = item.get_min_size()
                if item.expand:
                    w = width
                if item.proportion:
                    p = item.proportion / total_proportions
                    h += int(extra_height * p)
                if item.align == CENTER:
                    offset = width / 2 - w / 2
                    item.set_dimensions(x + offset, y, w, h)
                elif item.align == RIGHT:
                    item.set_dimensions(x + width - w, y, w, h)
                else: # LEFT
                    item.set_dimensions(x, y, w, h)
                y += h

class HorizontalSizer(BoxSizer):
    def __init__(self):
        super(HorizontalSizer, self).__init__(HORIZONTAL)

class VerticalSizer(BoxSizer):
    def __init__(self):
        super(VerticalSizer, self).__init__(VERTICAL)

class GridSizer(Sizer):
    def __init__(self, rows, cols, row_spacing=0, col_spacing=0):
        super(GridSizer, self).__init__()
        self.rows = rows
        self.cols = cols
        self.row_spacing = row_spacing
        self.col_spacing = col_spacing
        self.row_proportions = {}
        self.col_proportions = {}
    def set_row_proportion(self, row, proportion):
        self.row_proportions[row] = proportion
    def set_col_proportion(self, col, proportion):
        self.col_proportions[col] = proportion
    def get_rows_cols(self):
        rows, cols = self.rows, self.cols
        count = len(self.items)
        if rows <= 0:
            rows = count / cols + int(bool(count % cols))
        if cols <= 0:
            cols = count / rows + int(bool(count % rows))
        return (rows, cols)
    def get_row_col_sizes(self):
        rows, cols = self.get_rows_cols()
        row_heights = [0] * rows
        col_widths = [0] * cols
        positions = product(range(rows), range(cols))
        for item, (row, col) in zip(self.items, positions):
            w, h = item.get_min_size()
            row_heights[row] = max(h, row_heights[row])
            col_widths[col] = max(w, col_widths[col])
        return row_heights, col_widths
    def get_min_size(self):
        row_heights, col_widths = self.get_row_col_sizes()
        width = sum(col_widths) + self.col_spacing * (len(col_widths) - 1)
        height = sum(row_heights) + self.row_spacing * (len(row_heights) - 1)
        return (width, height)
    def layout(self):
        row_spacing, col_spacing = self.row_spacing, self.col_spacing
        min_width, min_height = self.get_min_size()
        extra_width = max(0, self.width - min_width)
        extra_height = max(0, self.height - min_height)
        rows, cols = self.get_rows_cols()
        row_proportions = [
            self.row_proportions.get(row, 0) for row in range(rows)]
        col_proportions = [
            self.col_proportions.get(col, 0) for col in range(cols)]
        total_row_proportions = float(sum(row_proportions))
        total_col_proportions = float(sum(col_proportions))
        row_heights, col_widths = self.get_row_col_sizes()
        for row, proportion in enumerate(row_proportions):
            if proportion:
                p = proportion / total_row_proportions
                row_heights[row] += int(extra_height * p)
        for col, proportion in enumerate(col_proportions):
            if proportion:
                p = proportion / total_col_proportions
                col_widths[col] += int(extra_width * p)
        row_y = [sum(row_heights[:i]) + row_spacing * i for i in range(rows)]
        col_x = [sum(col_widths[:i]) + col_spacing * i for i in range(cols)]
        positions = product(range(rows), range(cols))
        for item, (row, col) in zip(self.items, positions):
            x, y = self.x + col_x[col], self.y + row_y[row]
            w, h = col_widths[col], row_heights[row]
            item.set_dimensions(x, y, w, h)

def main():
    a = Box(10, 10)
    b = Box(25, 25)
    c = Box(50, 10)
    # sizer = VerticalSizer()
    sizer = GridSizer(2, 2)
    sizer.add(a)
    sizer.add(b)
    sizer.add(c)
    sizer.fit()
    print a.dimensions
    print b.dimensions
    print c.dimensions

if __name__ == '__main__':
    main()

########NEW FILE########
