"""Debug state transitions."""
from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.core.schema import EquipmentConfig
from virtual_factory.equipment.compressor_train import CompressorTrain

config = EquipmentConfig(
    id="COMP01", model_type="compressor_train_v1", display_name="Test",
    parameters={
        "rated_power_kw": 500, "rated_flow_m3_s": 2.0,
        "rated_pressure_ratio": 3.0, "polytropic_efficiency": 0.82,
        "source_equipment_id": "SRC", "sink_equipment_id": "SNK",
    },
)
train = CompressorTrain(config=config)
state = RuntimeState()
state.set_truth("SRC.pressure_kpa", 101.325)
state.set_truth("SRC.temperature_c", 25.0)
state.set_truth("SRC.molecular_weight_kg_kmol", 28.97)
state.set_truth("SRC.specific_heat_ratio", 1.4)
state.set_truth("SRC.available_flow_m3_s", 5.0)
state.set_truth("SNK.backpressure_kpa", 280.0)
train.initialize_state(state)
state.set_truth("COMP01.running", True)

for i in range(60):
    train.process_step(state, 1.0)
    if i < 15 or i % 10 == 0:
        flow = state.get_truth("COMP01.flow_m3_s")
        surge = state.get_truth("COMP01.surge_margin")
        print(f"Step {i+1:2d}: state={train.operating_state.value:15s} flow={flow:.2f} surge={surge:.3f}")
