import os
from argparse import ArgumentParser

import ai2thor
import compress_json
from ai2thor.controller import Controller
from ai2thor.hooks.procedural_asset_hook import ProceduralAssetHookRunner

from ai2holodeck.constants import (
    HOLODECK_BASE_DATA_DIR,
    THOR_COMMIT_ID,
    OBJATHOR_ASSETS_DIR,
)

parser = ArgumentParser()
parser.add_argument(
    "--scene",
    help="the directory of the scene to be generated",
    # default=os.path.join(
    #     HOLODECK_BASE_DATA_DIR, "data/scenes/a_high_school_building_with_si-2026-01-23-16-22-04-038491/a_high_school_building_with_si.json"
    # ),
     # the relative path to the scene json file in current repo
    # default="./data/scenes/a_high_school_building_with_si-2026-01-23-16-22-04-038491/a_high_school_building_with_si.json"
    # default="./data/scenes/a_living_room-2026-01-23-16-12-22-527091/a_living_room.json"
    default="./data/scenes/一个只有“table”桌子的房间-2026-02-03-11-52-57-923751/一个只有“table”桌子的房间.json"
)
parser.add_argument(
    "--asset_dir",
    help="the directory of the assets to be used",
    default=OBJATHOR_ASSETS_DIR,
)
args = parser.parse_args()

scene = compress_json.load(args.scene)

controller = Controller(
    commit_id=THOR_COMMIT_ID,
    start_unity=False,
    port=8200,
    scene="Procedural",
    gridSize=0.25,
    width=300,
    height=300,
    server_class=ai2thor.wsgi_server.WsgiServer,
    makeAgentsVisible=False,
    visibilityScheme="Distance",
    action_hook_runner=ProceduralAssetHookRunner(
        asset_directory=args.asset_dir,
        asset_symlink=True,
        verbose=True,
    ),
)

# Reset the controller to sync sequence IDs before taking steps
controller.reset()

controller.step(action="CreateHouse", house=scene)
print("controller reset")
