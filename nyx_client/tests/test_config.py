from contextlib import contextmanager
from io import IOBase
from os import PathLike, chdir, getcwd, makedirs, mkdir
from pathlib import PurePath
from tempfile import NamedTemporaryFile, TemporaryDirectory

import pytest

from nyx_client.configuration import BaseNyxConfig

TEST_CONFIG = {
    "NYX_URL": "https://mock.nyx.url",
    "NYX_EMAIL": "mock@email.com",
    "NYX_PASSWORD": "mock_password",
}


def test_base_config_from_env_not_found():
    with TemporaryDirectory() as dir:
        non_existing = str(PurePath(dir, "does_not_exist.env"))
        with pytest.raises(ValueError, match=f"Env file not found from specified path: {non_existing}"):
            BaseNyxConfig.from_env(env_file=non_existing)


def test_base_config_from_env_empty():
    with NamedTemporaryFile() as empty:
        with pytest.raises(ValueError, match=f"Env file empty: {empty.name}"):
            BaseNyxConfig.from_env(env_file=empty.name)


@pytest.mark.parametrize("missing_field", ("NYX_URL", "NYX_EMAIL", "NYX_PASSWORD"))
def test_base_config_from_env_has_missing_field(missing_field: str):
    with NamedTemporaryFile(mode="w") as partial:
        conf = TEST_CONFIG.copy()
        conf.pop(missing_field)
        write_conf_to_file(partial, conf)

        with pytest.raises(ValueError, match=f"{missing_field} not set in {partial.name}"):
            BaseNyxConfig.from_env(env_file=partial.name)


def test_base_config_from_env_loads_absolute_file():
    with NamedTemporaryFile(mode="w") as file:
        write_conf_to_file(file, TEST_CONFIG)
        conf = BaseNyxConfig.from_env(env_file=file.name)
        assert_config_matches_test_config(conf)


def test_base_config_from_env_does_not_search_in_parent_folders_with_absolute_file():
    env_file_name = "my.env"

    # Given a directory
    with TemporaryDirectory() as dir:
        # Containing a env file ..
        with open(PurePath(dir, env_file_name), mode="w") as file:
            write_conf_to_file(file, TEST_CONFIG)

        # .. and a sub-directory
        subdir = PurePath(dir, "test_sub_dir")
        mkdir(subdir)
        non_existing = str(PurePath(subdir, env_file_name))

        # If the subdirectory is the current one ..
        with working_directory(subdir):
            # .. an absolute env file specified within it should NOT result in the path higher up being checked
            with pytest.raises(ValueError, match=f"Env file not found from specified path: {non_existing}"):
                BaseNyxConfig.from_env(env_file=non_existing)


@pytest.mark.parametrize(
    "relative_env_file_name",
    (
        PurePath("my.env"),
        PurePath("subdir1", "my.env"),
        PurePath("subdir1", "subdir2", "my.env"),
    ),
)
def test_base_config_from_env_does_search_in_parent_folders_with_relative_file(relative_env_file_name: PurePath):
    # Given a directory
    with TemporaryDirectory() as dir:
        # Containing a env file in a subdirectory #1
        makedirs(PurePath(dir, relative_env_file_name.parent), exist_ok=True)
        with open(PurePath(dir, relative_env_file_name), mode="w") as file:
            write_conf_to_file(file, TEST_CONFIG)

        # .. and an empty subdirectory #2
        subdir = PurePath(dir, "empty_sub_dir")
        mkdir(subdir)

        # If current directory is subdirectory #2 ..
        with working_directory(subdir):
            # .. a relative env file should end up finding the env file in subdirectory #1
            conf = BaseNyxConfig.from_env(env_file=str(relative_env_file_name))
        assert_config_matches_test_config(conf)


def test_base_config_from_env_loads_workdir_file():
    with NamedTemporaryFile(mode="w") as file:
        write_conf_to_file(file, TEST_CONFIG)

        with working_directory(PurePath(file.name).parent):
            conf = BaseNyxConfig.from_env(env_file=file.name)
        assert_config_matches_test_config(conf)


def test_base_config_from_env_loads_workdir_file():
    with NamedTemporaryFile(mode="w") as file:
        write_conf_to_file(file, TEST_CONFIG)

        with working_directory(PurePath(file.name).parent):
            conf = BaseNyxConfig.from_env(env_file=file.name)
        assert_config_matches_test_config(conf)


def assert_config_matches_test_config(conf: BaseNyxConfig):
    assert conf.nyx_url == TEST_CONFIG["NYX_URL"]
    assert conf.nyx_email == TEST_CONFIG["NYX_EMAIL"]
    assert conf.nyx_password == TEST_CONFIG["NYX_PASSWORD"]


def write_conf_to_file(fp: IOBase, conf: dict[str, str]):
    fp.writelines(f"{field}={value}\n" for field, value in conf.items())
    fp.flush()


@contextmanager
def working_directory(dir: str | PathLike):
    previous = getcwd()
    chdir(dir)
    try:
        yield
    finally:
        chdir(previous)
