#!/bin/python3

import os
import sys
import yaml
import re
import subprocess
from argparse import ArgumentParser

# Create error message
def error(text: str):
    print("ERROR: " + text, file=sys.stderr)
    exit(1)

# Create banner text
def banner(text: str) -> str:
    if len(text) > 110:
        text = text[:110]
    sep = '########' + ''.join(['#' for _ in text])
    return "echo -e '\\n" + sep + "\\n### " + text + " ###\\n" + sep + "\\n'"

# Replace variables
def replace_with_variables(value: str, variables: dict, user_variables: dict) -> str:
    for v in user_variables:
        value = str(value).replace('{' + v + '}', user_variables[v])
    for v in variables:
        value = str(value).replace('{' + v + '}', variables[v])
    return value

# Extract variables
def extract_variables(root: dict, variables: dict, user_variables: dict) -> dict:
    if 'variables' in root:
        for var in root['variables']:
            variables[var] = replace_with_variables(str(root['variables'][var]), variables, user_variables)
    return variables

# Extract environment
def extract_environment(root: dict, environment: dict, variables: dict, user_variables: dict) -> dict:
    if 'environment' in root:
        for var in root['environment']:
            environment[var] = replace_with_variables(str(root['environment'][var]), variables, user_variables)
    return environment

# Get path value
def get_path(root: dict, variables: dict, user_variables: dict) -> str | None:
    if 'path' in root:
        path = os.path.expanduser(replace_with_variables(root['path'], variables, user_variables))
        regex = re.compile(path)
        match = regex.match(os.getcwd())
        return match.group() if match else None
    error('No path in ' + str(root))

# Get build steps
def get_build_steps(root: dict) -> list:
    steps = []
    if 'build' in root:
        for x in root['build']:
            steps.append(x)
    return steps

# Get test steps
def get_test_steps(root: dict) -> list:
    steps = []
    if 'test' in root:
        for x in root['test']:
            steps.append(x)
    return steps

# Execute command
def execute_command(cmd: str, cwd: str, environment: dict):
    print(cmd)
    env = {**os.environ, **environment}
    retcode = subprocess.call(cmd, env=env, cwd=cwd, shell=True)
    if retcode != 0:
        error('Execution of "' + cmd + '" failed.')

# Execute build steps
def build(proj_root: dict, path: str, variables: dict, environment: dict, user_variables: dict):
    # Skip if no build steps
    if not 'build' in proj_root:
        return

    cmd = []
    variables = extract_variables(proj_root, variables, user_variables)
    environment = extract_environment(proj_root, environment, variables, user_variables)

    for step in proj_root['build']:
        step = replace_with_variables(step, variables, user_variables)
        if len(cmd) > 0:
            cmd.append('&&')
        cmd.append(banner(step))
        cmd.append('&&')
        cmd.append(step)

    execute_command(' '.join(cmd), path, environment)

# Execute test steps
def test(proj_root: dict, path: str, variables: dict, environment: dict, user_variables: dict):
    # Skip if no test steps
    if not 'test' in proj_root:
        return

    cmd = []
    variables = extract_variables(proj_root, variables, user_variables)
    environment = extract_environment(proj_root, environment, variables, user_variables)

    for step in proj_root['test']:
        step = replace_with_variables(step, variables, user_variables)
        if len(cmd) > 0:
            cmd.append('&&')
        cmd.append(banner(step))
        cmd.append('&&')
        cmd.append(step)

    execute_command(' '.join(cmd), path, environment)

# Get system name
def get_system_name() -> str:
    return "fedora"

# Main entry point
def main():
    # Create argument parser
    parser = ArgumentParser(description='Builder script to execute custom builds.')
    parser.add_argument('--no-build', '-n', required=False, action='store_true', help='Perform no build.')
    parser.add_argument('--test', '-t', required=False, action='store_true', help='Execute test steps.')
    parser.add_argument('--variable', '-v', required=False, action='append', help='Custom variables.')
    parser.add_argument('--config', '-c', required=False, help='Custom configuration file.', default=os.path.expanduser('~/.builder-config.yml'))
    parser.add_argument('--operating-system', '-os', required=False, help='Operating system type.', default=get_system_name())
    parser.add_argument('--build-type', '-bt', required=False, help='Build type.', default='Release')
    args = parser.parse_args()

    # Create map of user specified variables
    user_variables = {}
    if args.variable:
        for v in args.variable:
            s = v.split('=', 1)
            user_variables[s[0]] = str(s[1]).strip()

    # Read configuration file
    with open(args.config, 'r') as file:
        config = yaml.safe_load(file)

    # Setup basic variables
    variables = {}
    variables['os'] = args.operating_system
    variables['bt'] = args.build_type

    # Setup variables and environment
    variables = extract_variables(config, variables, user_variables)
    environment = extract_environment(config, {}, variables, user_variables)

    # Loop over all projects
    for p in config['projects']:
        project = config['projects'][p]
        project_vars = extract_variables(project, variables, user_variables)
        path = get_path(project, project_vars, user_variables)
        # If path doesn't match, check next one
        if not path:
            continue
        # Perform build
        if not args.no_build:
            build(project, path, project_vars, environment, user_variables)
        # Execute tests
        if args.test:
            test(project, path, project_vars, environment, user_variables)
        # Porject is handled, return
        return
    error("No matching configuration entry found.")

if __name__ == '__main__':
    main()
