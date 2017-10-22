import logging
from pathlib import Path
from collections import namedtuple, defaultdict

from clint.textui import puts, indent, colored
from .utils import bold


logger = logging.getLogger(__name__)
Job = namedtuple('Job', 'folder path filters actions')


def all_pathes(rule):
    for folder in rule.folders:
        for path in Path(folder).expanduser().glob('*.*'):
            yield (folder, path)


def find_jobs(rules):
    for rule in rules:
        for folder, path in all_pathes(rule):
            if all(f.matches(path) for f in rule.filters):
                yield Job(
                    folder=folder, path=path, filters=rule.filters,
                    actions=rule.actions)


def sort_by_folder(jobs):
    result = defaultdict(list)
    for job in jobs:
        result[job.folder].append(job)
    return result


def execute_rules(rules, simulate: bool):
    # TODO: warning for multiple rules applying to the same path
    jobs = list(find_jobs(rules))
    if not jobs:
        puts('Nothing to do.')
        return

    jobs_by_folder = sort_by_folder(jobs)
    first = True
    for folder, jobs in sorted(jobs_by_folder.items()):
        # newline between folders
        if not first:
            puts()
        first = False

        puts('Folder %s:' % bold(folder))
        with indent(2):
            for job in jobs:
                puts('File %s:' % bold(job.path.name))
                with indent(2):
                    attrs = filter_pipeline(job)
                    action_pipeline(job=job, attrs=attrs, simulate=simulate)


def filter_pipeline(job):
    result = {}
    for filter_ in job.filters:
        result.update(filter_.parse(job.path))
    return result


def action_pipeline(job, attrs, simulate):
    try:
        current_path = job.path.resolve()
        for action in job.actions:
            new_path = action.run(
                path=current_path, attrs=attrs, simulate=simulate)
            if new_path is not None:
                current_path = new_path
    except Exception as e:
        logging.exception(e)
        action.print('%s %s' % (colored.red('ERROR!', bold=True), e))
