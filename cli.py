#!/usr/bin/env python3

import math
import os
import re
from typing import Union
from requests import Timeout
from manager import ModPackages, Package

ModPackages.init()


def _menu(
        title: str,
        options: Union[tuple, list],
        quit: bool = False,
        clear: bool = False,
        back: bool = False,
        default=None
):
    """
    Render a menu for the user

    Parameters
    ----------
    title : str
        Title to display at the top of the menu
    options : list,tuple
        List of menu options (option label, return value / return method)
        If the second parameter of the selected option is a function, that function is called when selected.
    quit : bool
        Display a "quit" option to immediately exit the application
    clear : bool
        Clear the display prior to displaying the menu, useful for the main menu
    back : bool
        Display a "back" option, will return None when selected
    default : str
        Default option to use if the user simply presses 'Enter' without selecting anything
        Note, this is what the user _would_ enter by default, so the 0th index will be '1'.
    """
    if clear:
        os.system('clear')

    print(title + '\n')

    space = math.floor(math.log10(len(options))) + 1

    c = 0
    for i in options:
        c += 1
        s = space - math.floor(math.log10(c))
        print(str(c) + ':' + (' ' * s) + i[0])

    if back:
        print('B: Go Back')

    if quit:
        print('Q: Quit Application')

    print('')
    opt = input('Enter 1-' + str(len(options)) + ': ')

    if opt == '':
        opt = default

    if quit and opt is not None and opt.lower() == 'q':
        print('Bye bye')
        exit()

    if back and opt is not None and opt.lower() == 'b':
        return None

    if clear:
        os.system('clear')
    else:
        print('')

    c = 0
    sel = None
    for i in options:
        c += 1
        if opt == str(c):
            sel = i[1]

    if hasattr(sel, '__call__'):
        return sel()
    else:
        return sel


def _wait():
    """
    Just wait until the user presses enter, useful for displaying information
    """
    print('')
    input('Press ENTER to continue')


def menu_main():
    """
    Present the user with the main menu of this application
    """
    run = _menu(
        'Valheim Mod Manager',
        (
            ('List Mods Installed', list_installed),
            ('Install New Mod', install_new),
            ('Check For Updates', check_updates),
            ('List Mods Removed', list_removed),
            ('Uninstall Mod', remove),
            ('Revert Modifications', rollback),
            # ('Sync Game Mods       [Local Game]', sync_game),
            # ('Import Game Mods     [Local Game]', import_existing),
            ('Export/Package Mods', export_package)
        ),
        quit=True, clear=True
    )

    if run == 'wait':
        _wait()


def check_environment():
    """
    Check the environment on starting to allow the user to sync existing mods easily

    Nothing is returned, but if the user selects the default option, `import_existing` will be executed
    """

    print('Checking manager environment...')
    if not ModPackages.check_packages_fresh():
        print('Thunderstore packages cache not fresh, downloading new copy...')
        try:
            ModPackages.download_packages()
        except ConnectionError:
            print('Unable to connect to Thunderstore!  Please verify your internet connectivity.')
        except Timeout:
            print('Thunderstore took too long to respond, skipping package update')

    print('Loading manager...')
    ModPackages.load_caches()

    print('Checking local game environment...')
    mods = []
    diff = False
    game = ModPackages.get_synced_packages()
    for pkg in game:
        if pkg.installed_version is None:
            # Mod in game directory is not registered as installed
            print(pkg.name + ' found in game but is not registered yet')
            diff = True
        elif pkg.installed_version != pkg.selected_version:
            # Mod installed, but versions differ
            print(pkg.name + ' ' + pkg.selected_version + ' found in game directory differs from registered version')
            diff = True

        mods.append(pkg.name)
    local = ModPackages.get_installed_packages()
    for pkg in local:
        # Skip auto-generated system mods
        if pkg.name == 'BepInExPack_Valheim' or pkg.name == 'HookGenPatcher':
            continue

        if pkg.name not in mods:
            print(pkg.name + ' registered but is not installed in game yet')
            diff = True

    if diff:
        _menu(
            title='Changes detected',
            options=(
                ('Sync changes', sync_existing),
                ('Continue without syncing', 'skip')
            ),
            default='1'
        )


def list_installed() -> str:
    """
    List installed mods (and provide a UI to manage them)
    :return: str
    """
    return _list_mods('installed')


def list_removed() -> str:
    """
    List recently removed mods (and provide a UI to manage them)
    :return: str
    """
    return _list_mods('removed')


def _list_mods(mode: str) -> str:
    """
    Display a list of mods

    Returns
    -------
    str
        'wait' is returned to indicate that the user needs to press 'Enter' to continue
    """

    max_len = {
        'name': 0,
        'vers': 0,
        'date': 0,
        'author': 0
    }

    def print_row(row: dict):
        print(
            '| ' +
            ' | '.join((
                row['id'].rjust(2, ' '),
                row['name'].ljust(max_len['name'], ' '),
                row['version'].ljust(max_len['vers'], ' '),
                row['date'].ljust(max_len['date'], ' '),
                row['rating'].rjust(6, ' '),
                row['author'].ljust(max_len['author'], ' ')
            )) +
            ' |'
        )

    def print_sep():
        print(
            '|-' +
            '-|-'.join((
                '-'.rjust(2, '-'),
                '-'.ljust(max_len['name'], '-'),
                '-'.ljust(max_len['vers'], '-'),
                '-'.ljust(max_len['date'], '-'),
                '-'.rjust(6, '-'),
                '-'.ljust(max_len['author'], '-')
            )) +
            '-|'
        )

    sorting = 'n'
    while True:
        os.system('clear')

        if mode == 'installed':
            mods = ModPackages.get_installed_packages()
        else:
            mods = ModPackages.get_removed_packages()

        if len(mods) == 0:
            if mode == 'installed':
                print(
                    'No mods are installed!  '
                    'Try running "Import Game Mods" to import your existing mods or "Install New Mod" to start!'
                )
            else:
                print('No mods recently removed')
            return 'wait'

        max_len = {
            'name': 8,
            'vers': 7,
            'date': 7,
            'author': 6
        }
        for pkg in mods:
            max_len['name'] = max(max_len['name'], len(pkg.name))
            if pkg.installed_version is not None:
                max_len['vers'] = max(max_len['vers'], len(pkg.installed_version))
            max_len['date'] = max(max_len['date'], len(pkg.update.strftime('%Y-%m-%d')))
            max_len['author'] = max(max_len['author'], len(pkg.owner))

        if mode == 'installed':
            print('Installed Mods')
        else:
            print('Removed Mods')
        print('')

        print_row({
            'id': '#',
            'name': 'Mod Name',
            'version': 'Version',
            'date': 'Updated',
            'rating': 'Rating',
            'author': 'Author'
        })
        print_sep()

        if sorting == 'v':
            mods = sorted(mods, key=lambda item: item.installed_version if item.installed_version is not None else '')
        elif sorting == 'd':
            mods = sorted(mods, key=lambda item: item.update)
        elif sorting == 'r':
            mods = sorted(mods, key=lambda item: item.rating)
        elif sorting == 'a':
            mods = sorted(mods, key=lambda item: item.owner)
        else:
            mods = sorted(mods, key=lambda item: item.name)

        counter = 1
        for pkg in mods:
            print_row({
                'id': str(counter),
                'name': pkg.name,
                'version': pkg.installed_version if pkg.installed_version is not None else 'N/A',
                'date': pkg.update.strftime('%Y.%m.%d'),
                'rating': str(pkg.rating),
                'author': pkg.owner
            })
            counter += 1

        print('')
        print('Change sorting by entering [n]ame, [v]ersion, [d]ate, [r]ating, or [a]uthor,')
        print('view or manage a mod with 1 - ' + str(counter-1) + ', or ENTER to return')
        opt = input('(n, v, d, r, a, 1-' + str(counter-1) + '): ').lower()

        if opt == '':
            # Return to menu
            return ''
        elif re.match('^[0-9]*$', opt) is not None and counter > int(opt) > 0:
            # Number, select a specific mod
            _manage_mod(mods[int(opt)-1])
        else:
            sorting = opt


def install_new():
    """
    Provide a UI to install a new mod from a search field

    Returns
    -------
    str|None
        'wait' is returned on changes to allow the user to see results,
        or None if nothing performed
    """
    print('Install New Mod')
    print('')
    opt = input('Enter the mod name or URL to install (or ENTER to return): ')

    if opt == '':
        return

    mod = None
    mods = ModPackages.search(opt)
    if len(mods) == 0:
        print('No mods found!')
        _wait()
        return install_new()
    elif len(mods) > 1:
        mods.sort(reverse=True, key=lambda mod: mod.rating)
        opts = []
        for m in mods:
            opts.append((m.name + ' by ' + m.owner + ' last updated ' + m.update.strftime('%Y-%m-%d'), m))
        opt = _menu(title='Multiple mods found', options=opts, back=True, default='b')

        if opt is None:
            return install_new()
        else:
            mod = opt
    else:
        mod = mods[0]

    opts = []
    for v in mod.versions:
        opts.append((v.version + ' released ' + v.created.strftime('%Y-%m-%d'), v))

    vers = _menu(title='Select Version (or ENTER to auto select newest)', options=opts, back=True, default='1')

    if vers is None:
        return

    mod.selected_version = vers.version
    print('Installing ' + mod.name + ' v' + vers.version)
    print(vers.description)
    print('')

    try:
        opt = input('ENTER to resume, CTRL+C to stop: ')
    except KeyboardInterrupt:
        opt = 'n'

    if opt == '':
        print('Installing mod...')
        mod.install()
        print('Deploying to local game client...')
        ModPackages.sync_game()
        print('Mod installed')
        return 'wait'
    else:
        print('not installing')


def export_package():
    """
    Export all changes to ZIP files for deployment

    Returns
    -------
    str
        'wait' is returned to indicate that the user needs to press 'Enter' to continue
    """
    print('Exporting mod packages...')
    conf = ModPackages.export_with_configs()
    full = ModPackages.export_full()
    updates = ModPackages.export_updates()
    changelog = ModPackages.export_changelog()
    modlist = ModPackages.export_modlist()

    try:
        if ModPackages.config['sftp_host'] != '':
            print('Uploading server packages to ' + ModPackages.config['sftp_host'] + '...')
            ModPackages.export_server_sftp()
        else:
            print('No SFTP host set, skipping server upload')
    except KeyError:
        print('No SFTP host set, skipping server upload')

    ModPackages.commit_changes()

    print('Created bundles:')
    print('Conf:      ' + conf)
    print('Full:      ' + full)
    print('Updates:   ' + updates)
    print('Changelog: ' + changelog)
    print('Modlist:   ' + modlist)
    return 'wait'


def check_updates() -> str:
    """
    Check if mods have updates and provide the user with an option to install them

    Returns
    -------
    str
        'wait' is returned to indicate that the user needs to press 'Enter' to continue
    """
    print('Checking for updates...')
    print('')
    updates_available = False
    opts = [('Install all updates', 'ALL')]
    for pkg in ModPackages.get_installed_packages():
        updates = pkg.check_update_available()
        v1 = pkg.get_installed_version().version
        v2 = pkg.get_highest_version().version

        if updates:
            opts.append((pkg.name + ' ' + v1 + ' update available to ' + v2, pkg))
            updates_available = True

    if not updates_available:
        print('No mod updates are available!')
        return 'wait'

    opt = _menu(title='Select an update to perform or ENTER to update all', options=opts, default='1', back=True)

    if opt is None:
        # User opted to not perform any updates
        return ''
    elif opt == 'ALL':
        # User opted to perform ALL updates
        for pkg in ModPackages.get_installed_packages():
            if pkg.check_update_available():
                pkg.upgrade()
                print('Updated ' + pkg.name)
        ModPackages.sync_game()
    else:
        # Specific package to update
        opt.upgrade()
        ModPackages.sync_game()
        print('Updated ' + opt.name)

    return 'wait'


def rollback() -> str:
    """
    Revert / rollback pending changes prior to deployment, useful for borked mods

    Returns
    -------
    str
        'wait' is returned to indicate that the user needs to press 'Enter' to continue
    """
    print('Checking for changes...')
    print('')
    updates_available = False
    opts = []
    pkgs = []
    opts.append(('Rollback everything', 'ALL'))
    for pkg in ModPackages.get_installed_packages():
        try:
            changes = ModPackages.changed[pkg.uuid]

            if changes['old'] == changes['new']:
                # Changes recorded, but must have already been rolled back
                continue
            elif changes['old'] is None:
                # New record
                opts.append(('Remove ' + pkg.name + ' ' + pkg.installed_version, pkg))
                pkgs.append(pkg)
                updates_available = True
            elif changes['new'] is None:
                # Removed record
                opts.append(('Reinstall ' + pkg.name + ' ' + changes['old'], pkg))
                pkgs.append(pkg)
                updates_available = True
            else:
                # Updated
                opts.append(('Revert ' + pkg.name + ' from ' + changes['new'] + ' to ' + changes['old'], pkg))
                pkgs.append(pkg)
                updates_available = True
        except KeyError:
            # No changes recorded, nothing to perform
            pass

    if not updates_available:
        print('No changes found')
        return 'wait'

    opt = _menu(title='Select an update to revert or ENTER to rollback everything', options=opts, default='1',
                back=True)

    if opt is None:
        # User opted to not perform any updates
        return ''
    elif opt == 'ALL':
        # User opted to perform ALL updates
        for pkg in pkgs:
            pkg.rollback()
            print('Reverted ' + pkg.name)
        ModPackages.sync_game()
    else:
        # Specific package to update
        opt.rollback()
        ModPackages.sync_game()
        print('Reverted ' + opt.name)

    return 'wait'


def remove() -> str:
    """
    Provide a UI for the user to remove an installed mod

    Returns
    -------
    str
        'wait' is returned to indicate that the user needs to press 'Enter' to continue
    """
    pkgs = ModPackages.get_installed_packages()
    opts = []
    c = -1
    for pkg in pkgs:
        c += 1
        opts.append((pkg.name + ' ' + pkg.installed_version, c))

    if len(opts) == 0:
        print('No mods installed, nothing to remove.')
        return 'wait'

    opts.append(('**REMOVE ALL MODS**', '_ALL_'))

    opt = _menu(title='Uninstalling Mod', options=opts, back=True, default='b')

    if opt is None:
        return ''

    if opt == '_ALL_':
        for pkg in pkgs:
            print('Removing mod ' + pkg.name + '...')
            pkg.remove()
    else:
        print('Removing mod...')
        pkgs[opt].remove()

    print('Removing files from game client...')
    ModPackages.sync_game()
    print('Selected mod has been removed')
    return 'wait'


def import_existing() -> str:
    """
    Load all currently installed game mods into the manager, useful on first run and if a mod is manually installed

    Returns
    -------
    str
        'wait' is returned to indicate that the user needs to press 'Enter' to continue
    """
    print('Scanning for current packages...')
    packages = ModPackages.get_synced_packages()

    check = []
    dupes = []
    for p in packages:
        if p.name in check and p.name not in dupes:
            dupes.append(p.name)
        else:
            check.append(p.name)

    if len(dupes) > 0:
        # The manifest doesn't contain all data to uniquely identify the source package,
        # and some authors will fork projects to publish under the same name.
        for d in dupes:
            opts = []
            for p in packages:
                if p.name == d:
                    opts.append((p.name + ' by ' + p.owner + ' last updated ' + p.update.strftime('%Y-%m-%d'), p))
            opt = _menu(title='Duplicates found for package, please select the one to install', options=opts)

            # Since we can't modify a list while iterating over, (and modifying it will change the keys),
            # create a copy list and copy valid entries over
            p1 = []
            for p in packages:
                if p.name != d or p == opt:
                    p1.append(p)
            packages = p1

    print('')
    for p in packages:
        print('* ' + p.name + ' ' + p.selected_version)

    if len(packages) > 0:
        try:
            opt = input('ENTER to load current mods, CTRL+C to stop: ')
        except KeyboardInterrupt:
            opt = 'n'
    else:
        opt = 'n'

    if opt == '':
        for p in packages:
            print('Installing ' + p.name + ' ' + p.selected_version + '...')
            p.install()

        return 'wait'


def sync_existing() -> str:
    """
    Import any existing game mod and push any registered mod
    :return:
    """
    import_existing()
    ModPackages.sync_game()
    return ''


def _manage_mod(mod: Package):
    os.system('clear')
    if mod.installed_version is not None:
        print(mod.name + ' ' + mod.installed_version)
    else:
        print(mod.name)
    print('')
    if mod.check_update_available():
        print('Status: Update Available!')
    elif mod.installed_version is not None:
        print('Status: Installed, Up to date')
    else:
        print('Status: Not installed')
    print('Author: ' + mod.owner)
    print('Updated: ' + mod.update.strftime('%Y-%m-%d'))
    print('Rating: ' + str(mod.rating))
    print('Categories: ' + ', '.join(mod.categories))
    print('URL: ' + mod.url)
    print('')
    if mod.installed_version is not None:
        print(mod.get_installed_version().description)
    else:
        print(mod.get_highest_version().description)

    print('')
    if mod.check_update_available():
        options = ('r', 'u')
        print('Actions: [r]emove, [u]pdate, or ENTER to return')
    elif mod.installed_version is not None:
        options = ('r',)
        print('Actions: [r]emove or ENTER to return')
    else:
        options = ('i',)
        print('Actions: [i]nstall for the latest version or ENTER to return')
    opt = input('(' + ', '.join(options) + ', or ENTER): ').lower()

    if opt == 'r' and opt in options:
        print('Removing mod...')
        mod.remove()

        print('Removing files from game client...')
        ModPackages.sync_game()

        print('Selected mod has been removed')
        _wait()
    elif opt == 'u' and opt in options:
        print('Updating mod...')
        mod.upgrade()

        print('Syncing game client...')
        ModPackages.sync_game()

        print('Updated ' + mod.name)
        _wait()
    elif opt == 'i' and opt in options:
        print('Installing mod...')
        mod.install()

        print('Syncing game client...')
        ModPackages.sync_game()

        print('Mod installed')
        _wait()


# Check if the user performed manual changes first (also useful on first run)
check_environment()

# Run the main menu until they quit.
while True:
    menu_main()
