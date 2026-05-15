import nav_planning.local_planner


def test_nav_planning_imports():
    assert hasattr(nav_planning.local_planner, "LocalPlanner")
    assert callable(nav_planning.local_planner.main)
