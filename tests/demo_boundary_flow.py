"""Quick boundary flow test for compressor train."""
from virtual_factory.core.config_loader import load_plant_config
from virtual_factory.core.simulation_engine import SimulationEngine

config = load_plant_config("configs/plants/compressor_train_benchmark_01.yaml")
engine = SimulationEngine(config, dt_s=1.0)
engine.initialize()
st = engine.assembly.state

st.set_truth("COMP01.running", True)

for _ in range(10):
    engine.step()

sp = st.get_truth("COMP01.suction_pressure_kpa")
dp = st.get_truth("COMP01.discharge_pressure_kpa")
flow = st.get_truth("COMP01.flow_m3_s")
power = st.get_truth("COMP01.power_consumed_kw")
sink_flow = st.get_truth("GAS_SINK.flow_m3_s")
vib = st.get_truth("COMP01.vibration_de_mm_s")
motor = st.get_truth("COMP01.motor.current_a")
source_p = st.get_truth("GAS_SOURCE.pressure_kpa")
sink_bp = st.get_truth("GAS_SINK.backpressure_kpa")

print("=== Compressor Train — 10-Step Boundary Flow ===")
print(f"GAS_SOURCE pressure:      {source_p} kPa")
print(f"GAS_SINK backpressure:    {sink_bp} kPa")
print(f"---")
print(f"Suction pressure:         {sp:.1f} kPa")
print(f"Discharge pressure:       {dp:.1f} kPa")
print(f"Pressure ratio:           {dp/sp:.2f}")
print(f"Flow (COMP01):            {flow:.4f} m3/s")
print(f"Flow (GAS_SINK):          {sink_flow:.4f} m3/s")
print(f"Power consumed:           {power:.1f} kW")
print(f"Motor current:            {motor:.1f} A")
print(f"Vibration DE:             {vib:.2f} mm/s")
print(f"Operating hours:          {st.get_truth('COMP01.operating_hours'):.4f}")
print()
print("Graph flow: GAS_SOURCE -> COMP01 -> GAS_SINK : PASS")
