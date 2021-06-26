import sublime
import sublime_plugin
import threading
import os
import re
import subprocess

class EditorLineInputHandler(sublime_plugin.ListInputHandler):
    def name(self):
        return "pos"

    def placeholder(self):
        return "Search content line..."

    def list_items(self):
        window = sublime.active_window()
        view = window.active_view()
        regions = view.find_all('.+\n')
        lines = [view.substr(region).strip().replace('\t', '') for region in regions]
        positions = [r.begin() for r in regions]
        return [
            sublime.ListInputItem(
                text=line_str,
                value=pos,
            ) for pos, line_str in zip(positions, lines)
            if re.match('\s*\d+$', line_str) is None
        ]

class FuzzyLineCommand(sublime_plugin.WindowCommand):
    def run(self, pos):
        self.window.active_view().sel().clear()
        self.window.active_view().sel().add(sublime.Region(pos))
        self.window.active_view().show_at_center(sublime.Region(pos))

    def input(self, args):
        if "pos" not in args:
            return EditorLineInputHandler()
        else:
            return None

class GrepFileLinesThread(threading.Thread):
    def __init__(self, folder, filename, timeout=30):
        self.folder = folder
        self.filename = filename.decode('utf-8')
        self.rel_filename = self.filename.replace(folder, '')
        self.timeout = timeout
        self.result = None
        threading.Thread.__init__(self)

    def run(self):
        liens = []
        with open(self.filename, 'r', encoding='utf-8') as fs:
            try:
                lines = fs.readlines()
                self.result = [
                    sublime.ListInputItem(
                        text=line_str.strip().replace('\t', ''),
                        value=(self.filename, line_no + 1),
                        annotation='%s:%s'%(self.rel_filename, line_no+1),
                    ) for line_no, line_str in enumerate(lines)
                    if len(line_str.strip()) > 0
                ]
            except UnicodeDecodeError:
                self.result = []

class FolderLineInputHandler(sublime_plugin.ListInputHandler):
    def name(self):
        return "file_lines"

    def placeholder(self):
        return "Search content line..."

    def list_items(self):
        window = sublime.active_window()
        folder = window.folders()[0]
        rg_files = subprocess.check_output('rg --files %s'%folder, shell=True)
        file_list = rg_files.split(b'\n')
        threads = []
        for file in file_list:
            if not os.path.exists(file):
                continue
            thread = GrepFileLinesThread(folder, file)
            thread.start()
            threads.append(thread)

        lines = []
        for thread in threads:
            thread.join()
            lines += thread.result

        return lines

class FuzzyProjectLineCommand(sublime_plugin.WindowCommand):
    def run(self, file_lines):
        file = file_lines[0]
        line = file_lines[1]
        view = self.window.open_file(file)
        self._go_to_file_line(view, line)

    def _go_to_file_line(self, view, line):
        if view.is_loading():
            sublime.set_timeout_async(
                lambda: self._go_to_file_line(view, line),
                50
            )
            return
        # Convert from 1 based to a 0 based line number
        line = int(line) - 1

        # Negative line numbers count from the end of the buffer
        if line < 0:
            lines, _ = view.rowcol(view.size())
            line = lines + line + 1

        pt = view.text_point(line, 0)

        view.sel().clear()
        view.sel().add(sublime.Region(pt))

        view.show_at_center(pt)
        
    def input(self, args):
        if "file_lines" not in args:
            return FolderLineInputHandler()
        else:
            return None






























