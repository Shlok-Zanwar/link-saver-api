from loguru import logger
from .alchemy import Base

try:
    # address = Base.classes.address
    users_table = Base.classes.users
    links_table = Base.classes.links
    tags_table = Base.classes.tags
    link_tag_mapping_table = Base.classes.link_tag_mapping
    # links_tags_mapping_table = "Base.classes.links_tags_mapping"
    pass


except Exception as err:
    logger.error("error while creating models - {}".format(err))
