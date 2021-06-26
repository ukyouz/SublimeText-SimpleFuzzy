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
            if re.match('\s*\d+$', line_str) is None and len(line_str)
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
    def __init__(self, folder, filename, encoding='UTF-8', timeout=30):
        self.folder = folder
        self.filename = filename
        self.encoding = encoding
        self.rel_filename = self.filename.replace(folder, '')
        self.timeout = timeout
        self.result = None
        threading.Thread.__init__(self)

    def run(self):
        liens = []
        with open(self.filename, 'r', encoding=self.encoding) as fs:
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
        folders = window.folders()
        if len(folders) == 0:
            sublime.error_message('No project folder found for Fuzzy Project Line search.')
            return []
        active_view = window.active_view()
        active_folder = next(
            (f for f in folders if f in (active_view.file_name() or '')),
            folders[0]
        )
        encoding = active_view.encoding() if active_view.encoding() != 'Undefined' else 'UTF-8'
        print('fuzzy project in: %s with Encoding=%s'%(active_folder, encoding))
        file_list = self._list_files(active_folder, encoding)
        threads = []
        for file in file_list:
            if not os.path.exists(file):
                continue
            thread = GrepFileLinesThread(active_folder, file, encoding)
            thread.start()
            threads.append(thread)

        lines = []
        for thread in threads:
            thread.join()
            lines += thread.result

        return lines

    # return filenames including folder name
    def _list_files(self, folder, encoding='UTF-8'):
        OK = 0
        if os.system('which rg') == OK:
            rg_files = subprocess.check_output(
                'rg --files %s'%folder, shell=True
            ).splitlines()
            file_list = [f.decode(encoding) for f in rg_files]
        if os.system('git -C %s status'%folder) == OK:
            git_files = subprocess.check_output(
                'git -C %s ls-files'%folder, shell=True
            ).splitlines()
            file_list = [os.path.join(folder, f.decode(encoding)) for f in git_files]
        else:
            file_list = [f[0] for f in os.walk(folder)]

        return file_list

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






























