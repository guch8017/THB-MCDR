import json
import os.path
from typing import Dict, Optional

from mcdreforged.api.utils import serialize, deserialize

from lazybing_thb.location import Location
from lazybing_thb.storage.abstract_player_storage import AbstractPlayerStorage
from lazybing_thb.utils import logger


class PlayerHomeStorage(AbstractPlayerStorage):

    DEFAULT_HOME_KEY = '__default__'

    expected_type = Dict[str, Location]

    def __init__(self, player: str):
        super().__init__(player)
        self.__cached_data = None

    @classmethod
    def get_folder_name(cls):
        return "home"

    def get_file_path(self):
        return os.path.join(self.get_folder_path(), f"{self.player}.json")

    def save(self, data: Optional[expected_type] = None):
        with self.lock():
            if data is None:
                data = self.__cached_data
            with self.open('w') as f:
                json.dump(serialize(data), f, ensure_ascii=False, indent=4)

    def __initialize_data(self):
        # No lock acquire is needed
        self.save({})

    def get_data(self):
        with self.lock():
            if self.__cached_data is None:
                self.__cached_data = self._get_data()
            return self.__cached_data

    def _get_data(self) -> expected_type:
        with self.lock():
            self.ensure_file()
            if not self.exists():
                self.__initialize_data()
            with self.open() as f:
                try:
                    return deserialize(json.load(f), cls=self.expected_type)
                except (TypeError, ValueError) as exc:
                    logger.exception(f"Invalid data found in player home file: {self.player}.json", exc_info=exc)
                    self.__initialize_data()
                    return {}

    def get_home(self, home_name: str, default: Optional[Location] = None) -> Location:
        with self.lock():
            data = self.get_data()
            return data.get(home_name, default)

    def set_home(self, home_name: str, home_coordinates: Location) -> bool:
        with self.lock():
            data = self.get_data()
            if home_name == PlayerHomeStorage.DEFAULT_HOME_KEY:
                # 不能使用默认家的名字
                return False
            if home_name in data.keys():
                return False
            data[home_name] = home_coordinates
            if len(data) == 1:
                # 第一个家，设置为默认
                data[PlayerHomeStorage.DEFAULT_HOME_KEY] = home_name
            self.save()
            return True

    def remove_home(self, home_name: str) -> bool:
        with self.lock():
            data = self.get_data()
            if home_name not in data.keys():
                return False
            del data[home_name]
            if data.get(PlayerHomeStorage.DEFAULT_HOME_KEY) == home_name:
                del data[PlayerHomeStorage.DEFAULT_HOME_KEY]
            self.save()
            return True
        
    def set_default(self, home_name: str) -> bool:
        """
        将<home_name>设置为默认家
        """
        with self.lock():
            data = self.get_data()
            if home_name not in data.keys():
                # 不存在指定点位，失败
                return False
            data[PlayerHomeStorage.DEFAULT_HOME_KEY] = home_name
            self.save()
            return True
        
    def get_default(self, default: Optional[Location] = None) -> Location:
        """
        返回设置的默认家
        """
        with self.lock():
            data = self.get_data()
            default_home_name = data.get(PlayerHomeStorage.DEFAULT_HOME_KEY)
            if default_home_name is None:
                # 未设置默认家
                return default
            loc = data.get(default_home_name)
            if loc is None:
                # 防止意外情况
                return default
            return loc
            