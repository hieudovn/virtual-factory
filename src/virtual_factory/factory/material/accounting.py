"""Deterministic stock, capacity, reservation and recipe accounting."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal

from virtual_factory.factory.material.models import (
    Buffer,
    CapacityError,
    MaterialItem,
    MaterialValidationError,
    Recipe,
    RecipeError,
    Reservation,
    ReservationState,
    Unit,
)


def active_reserved_quantities(
    reservations: Mapping[str, Reservation],
) -> dict[str, Decimal]:
    reserved: dict[str, Decimal] = {}
    for reservation in reservations.values():
        if reservation.state is not ReservationState.ACTIVE:
            continue
        for leg in reservation.legs:
            if leg.quantity <= 0:
                continue
            reserved[leg.material_id] = (
                reserved.get(leg.material_id, Decimal("0")) + leg.quantity
            )
    return reserved


def available_quantity(
    item: MaterialItem, reserved: Mapping[str, Decimal]
) -> Decimal:
    return item.quantity - reserved.get(item.material_id, Decimal("0"))


def buffer_occupancy(
    items: Mapping[str, MaterialItem], location: str, unit: Unit
) -> Decimal:
    total = Decimal("0")
    for item in items.values():
        if (
            item.location == location
            and item.unit is unit
            and item.quantity > 0
            and item.lifecycle.value in {"PRODUCED", "RETURNED"}
        ):
            total += item.quantity
    return total


def check_buffer_capacity(
    buffer: Buffer,
    items: Mapping[str, MaterialItem],
    unit: Unit,
    additional: Decimal,
    material_type: str,
) -> None:
    if buffer.allowed_material_types is not None and (
        material_type not in buffer.allowed_material_types
    ):
        raise CapacityError(
            f"buffer {buffer.location_id!r} does not accept {material_type!r}"
        )
    if buffer.capacity is None:
        return
    if buffer.unit is not unit:
        raise CapacityError(
            f"buffer {buffer.location_id!r} uses {buffer.unit.value}, "
            f"not {unit.value}"
        )
    occupancy = buffer_occupancy(items, buffer.location_id, unit)
    if occupancy + additional > buffer.capacity:
        raise CapacityError(
            f"buffer {buffer.location_id!r} capacity {buffer.capacity} "
            f"would be exceeded by {additional} {unit.value}"
        )


def _leg_key(material_type: str, unit: Unit, quantity: Decimal) -> tuple:
    return (material_type, unit.value, quantity)


def _expected_keys(
    legs: Sequence[tuple[str, Unit, Decimal]],
) -> list[tuple]:
    return sorted(_leg_key(*leg) for leg in legs)


def validate_recipe_legs(
    recipe: Recipe,
    inputs: Sequence[tuple[str, Unit, Decimal]],
    outputs: Sequence[tuple[str, Unit, Decimal]],
) -> None:
    expected_inputs = _expected_keys(
        (leg.material_type, leg.unit, leg.quantity) for leg in recipe.inputs
    )
    expected_outputs = _expected_keys(
        (leg.material_type, leg.unit, leg.quantity) for leg in recipe.outputs
    )
    actual_inputs = _expected_keys(inputs)
    actual_outputs = _expected_keys(outputs)
    if actual_inputs != expected_inputs:
        raise RecipeError(
            f"transform inputs do not match recipe {recipe.recipe_revision!r}"
        )
    if actual_outputs != expected_outputs:
        raise RecipeError(
            f"transform outputs do not match recipe {recipe.recipe_revision!r}"
        )
    if recipe.scrap:
        expected_scrap = _expected_keys(
            (leg.material_type, leg.unit, leg.quantity) for leg in recipe.scrap
        )
        if not expected_scrap:
            raise RecipeError("recipe scrap declaration is invalid")
    for input_type, input_unit, input_quantity in inputs:
        for output_type, output_unit, output_quantity in outputs:
            if input_type == output_type and input_unit is output_unit:
                expected = input_quantity * recipe.yield_ratio
                if output_quantity != expected:
                    raise RecipeError(
                        f"recipe yield for {input_type!r} would be "
                        f"{output_quantity}, expected {expected}"
                    )


def require_nonnegative(value: Decimal, name: str) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise MaterialValidationError(f"{name} must be finite and >= 0")
    return value
