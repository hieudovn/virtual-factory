"""Tests for the Asset Hierarchy System."""

from virtual_factory.equipment.asset_hierarchy import AssetNode, AssetHierarchy


class TestAssetNode:
    def test_create_node(self):
        node = AssetNode("COMP01", "compressor_train", "Compressor Train A")
        assert node.asset_id == "COMP01"
        assert node.asset_type == "compressor_train"
        assert node.is_root is True
        assert node.is_leaf is True

    def test_add_child(self):
        root = AssetNode("TRAIN01", "compressor_train", "Train A")
        child = AssetNode("MOTOR", "driver_motor", "Main Motor",
                          equipment_ref="MTR01")
        root.add_child(child)
        assert child.parent is root
        assert root.is_leaf is False
        assert child.is_leaf is True
        assert child.path == "TRAIN01.MOTOR"

    def test_nested_path(self):
        root = AssetNode("A", "root")
        b = AssetNode("B", "type_b")
        c = AssetNode("C", "type_c")
        root.add_child(b)
        b.add_child(c)
        assert c.path == "A.B.C"

    def test_get_descendant_tags(self):
        root = AssetNode("TRAIN01", "train", tags=["TRAIN01.running"])
        motor = AssetNode("MOTOR", "motor", tags=["TRAIN01.motor.current_a"])
        bearing = AssetNode("BRG_DE", "bearing", tags=["TRAIN01.bearing_de_temp_c"])
        root.add_child(motor)
        motor.add_child(bearing)

        all_tags = root.get_descendant_tags()
        assert len(all_tags) == 3
        assert "TRAIN01.running" in all_tags
        assert "TRAIN01.motor.current_a" in all_tags

    def test_find(self):
        root = AssetNode("ROOT", "root")
        child = AssetNode("CHILD", "child")
        root.add_child(child)
        assert root.find("CHILD") is child
        assert root.find("NONEXISTENT") is None

    def test_flatten(self):
        root = AssetNode("ROOT", "root")
        a = AssetNode("A", "type")
        b = AssetNode("B", "type")
        root.add_child(a)
        root.add_child(b)
        flat = root.flatten()
        assert len(flat) == 3

    def test_to_dict(self):
        node = AssetNode("COMP01", "compressor_train", "Train A",
                         equipment_ref="COMP01_EQ")
        d = node.to_dict()
        assert d["asset_id"] == "COMP01"
        assert d["asset_type"] == "compressor_train"
        assert d["equipment_ref"] == "COMP01_EQ"
        assert d["is_leaf"] is True


class TestAssetHierarchy:
    def test_add_root(self):
        hierarchy = AssetHierarchy()
        root = hierarchy.add_root("TRAIN01", "compressor_train", "Train A")
        assert hierarchy.find("TRAIN01") is root
        assert len(hierarchy.roots) == 1

    def test_multiple_roots(self):
        hierarchy = AssetHierarchy()
        hierarchy.add_root("COMP01", "compressor_train", "Compressor A")
        hierarchy.add_root("PUMP01", "pump_system", "Pump A")
        assert len(hierarchy.roots) == 2

    def test_flatten(self):
        hierarchy = AssetHierarchy()
        root = hierarchy.add_root("TRAIN01", "train")
        child = AssetNode("MOTOR", "motor")
        root.add_child(child)
        hierarchy.add_node(child)

        flat = hierarchy.flatten()
        assert len(flat) == 2

    def test_get_all_tags(self):
        hierarchy = AssetHierarchy()
        root = hierarchy.add_root("TRAIN01", "train", "Train A")
        root.tags = ["TRAIN01.running", "TRAIN01.flow"]
        motor = AssetNode("MOTOR", "motor",
                          tags=["TRAIN01.motor.current_a"])
        root.add_child(motor)
        hierarchy.add_node(motor)

        tags = hierarchy.get_all_tags()
        assert len(tags) == 3
        assert hierarchy.get_tag_count() == 3

    def test_export_metadata(self):
        hierarchy = AssetHierarchy()
        hierarchy.add_root("TRAIN01", "compressor_train", "Train A")
        meta = hierarchy.export_metadata()
        assert len(meta) == 1
        assert meta[0]["asset_id"] == "TRAIN01"
