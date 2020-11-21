import click
from multiprocessing import Pool, cpu_count
import os

from lib.utils import get_files_to_process, get_kv_pairs


def assemble_new_filepath(old_filepath, kv_pairs):
    split_path = old_filepath.split("/")
    kv_pairs = ["{%s}" % pair for pair in kv_pairs]
    new_filename = ".".join(["".join(kv_pairs), old_filepath.split(".")[-1]])
    new_filepath = "/".join(split_path[:-1] + [new_filename])
    return new_filepath


def append_or_change_filenames(dir, key, newkey, value):
    for file in dir["files"]:
        append_or_change_filename(file, key, newkey, value)


def append_or_change_filename(file, key, newkey, value):
    appendix = "%s_%s" % (key, value)
    override = False
    kv_pairs = get_kv_pairs(file)
    keys = [pair.split("_")[0] for pair in kv_pairs]
    values = [pair.split("_")[1] for pair in kv_pairs]
    for i, existing_key in enumerate(keys):
        if existing_key == key and newkey is not None:
            override = True
            existing_value = values[i]
            kv_pairs[i] = "%s_%s" % (newkey, existing_value)
            break
        elif existing_key == key and newkey is None:
            override = True
            kv_pairs[i] = "%s_%s" % (key, value)
            break
    if not override:
        kv_pairs.append(appendix)
    new_filepath = assemble_new_filepath(file, kv_pairs)
    os.rename(file, new_filepath)
    return new_filepath


def delete_key(dir, key):

    for file in dir["files"]:
        split_path = file.split("/")
        filename = split_path[-1]
        kv_string = filename.split(".")[0]
        kv_pairs = get_kv_pairs(kv_string)
        for i, pair in enumerate(kv_pairs):
            if pair.split("_")[0] == key:
                kv_pairs.pop(i)
                break
        new_filepath = assemble_new_filepath(file, kv_pairs)
        os.rename(file, new_filepath)


def do_uid_insert(dir, uid_insert):
    for file in dir["files"]:
        split_path = file.split("/")
        filename = split_path[-1]
        kv_string = filename.split(".")[0]
        kv_pairs = get_kv_pairs(kv_string)
        for i, pair in enumerate(kv_pairs):
            if pair.split("_")[0].lower() == "uid":
                old_uid = pair.split("_")[1]
                new_uid = "-".join(
                    old_uid.split("-")[:-1] + [uid_insert] + [old_uid.split("-")[-1]]
                )
                kv_pairs[i] = "_".join(["UID", new_uid])
        new_filepath = assemble_new_filepath(file, kv_pairs)
        os.rename(file, new_filepath)


def replace_uid_year(dir, uid_year):
    for file in dir["files"]:
        split_path = file.split("/")
        filename = split_path[-1]
        kv_string = filename.split(".")[0]
        kv_pairs = get_kv_pairs(kv_string)
        for i, pair in enumerate(kv_pairs):
            if pair.split("_")[0].lower() == "uid":
                old_uid = pair.split("_")[1]
                new_uid = "-".join(old_uid.split("-")[:-1] + [str(uid_year)])
                kv_pairs[i] = "_".join(["UID", new_uid])
        new_filepath = assemble_new_filepath(file, kv_pairs)
        os.rename(file, new_filepath)


@click.command()
@click.option(
    "--src",
    "-s",
    type=click.Path(exists=True),
    help="source directory of images to process",
)
@click.option("--deletekey", "-dk", help="The key to delete.")
@click.option("--key", "-k", help="The key.")
@click.option("--newkey", "-nk", help="New key to overwrite 'key'.")
@click.option("--uid-insert", help="Value to insert into UID before the year.")
@click.option(
    "--uid-year", help="Value to replace the year in the UID with.", type=click.INT
)
@click.option("--value", "-v", help="The value. Leave blank to remove the key.")
def run(src, deletekey, key, newkey, uid_insert, uid_year, value):
    if src is None:
        click.secho("No source specified...", fg="red")
        click.echo("run 'python append.py --help to see options'")
        return

    if deletekey is not None:
        if click.confirm("Are you sure you want to delete key '%s'" % deletekey):
            subdirs = get_files_to_process(src)
            with Pool(processes=cpu_count()) as pool:
                pool.starmap(delete_key, [(dir, deletekey) for dir in subdirs])
        return

    if key is not None and newkey is not None:
        if click.confirm(
            "Are you sure you want to replace the key '%s' with '%s'" % (key, newkey)
        ):
            pass
        else:
            return

    if (key is not None and value is not None) or (
        key is not None and newkey is not None
    ):
        subdirs = get_files_to_process(src)
        with Pool(processes=cpu_count()) as pool:
            pool.starmap(
                append_or_change_filenames,
                [(dir, key, newkey, value) for dir in subdirs],
            )
        return
    if uid_insert is not None:
        subdirs = get_files_to_process(src)
        with Pool(processes=cpu_count()) as pool:
            pool.starmap(do_uid_insert, [(dir, uid_insert) for dir in subdirs])
        return
    if uid_year is not None:
        subdirs = get_files_to_process(src)
        with Pool(processes=cpu_count()) as pool:
            pool.starmap(replace_uid_year, [(dir, uid_year) for dir in subdirs])
        return
    else:
        click.secho("I'm afraid I don't quite know what to do.", fg="red")
        click.echo("run 'python append.py --help to see options'")


if __name__ == "__main__":

    run()
