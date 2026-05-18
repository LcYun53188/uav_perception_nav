import nav_planning.local_planner
import nav_planning.se2_dwa_local_planner


def test_nav_planning_imports():
    assert hasattr(nav_planning.local_planner, "LocalPlanner")
    assert callable(nav_planning.local_planner.main)
    assert hasattr(nav_planning.se2_dwa_local_planner, "SE2DWALocalPlanner")
    assert callable(nav_planning.se2_dwa_local_planner.main)
