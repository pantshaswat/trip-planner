import { useState } from 'react';
import AutocompleteInput from './AutocompleteInput';
import './TripForm.css';

const EMPTY = {
  current_location: '',
  pickup_location: '',
  dropoff_location: '',
  current_cycle_used: '',
};

const FIELDS = [
  { name: 'current_location', label: 'Current location', placeholder: 'e.g. Chicago, IL' },
  { name: 'pickup_location', label: 'Pickup location', placeholder: 'e.g. Joliet, IL' },
  { name: 'dropoff_location', label: 'Dropoff location', placeholder: 'e.g. St. Louis, MO' },
];

/**
 * The 4-field driver input form. Calls `onSubmit(payload)` with cleaned values.
 * `loading` disables the form while a plan is being fetched.
 */
export default function TripForm({ onSubmit, loading }) {
  const [values, setValues] = useState(EMPTY);

  function update(name, value) {
    setValues((v) => ({ ...v, [name]: value }));
  }

  function handleSubmit(e) {
    e.preventDefault();
    if (loading) return;
    onSubmit({
      current_location: values.current_location.trim(),
      pickup_location: values.pickup_location.trim(),
      dropoff_location: values.dropoff_location.trim(),
      current_cycle_used: Number(values.current_cycle_used),
    });
  }

  return (
    <form className="trip-form" onSubmit={handleSubmit} noValidate>
      {FIELDS.map((f) => (
        <AutocompleteInput
          key={f.name}
          label={f.label}
          placeholder={f.placeholder}
          value={values[f.name]}
          onChange={(v) => update(f.name, v)}
          disabled={loading}
        />
      ))}

      <label className="field">
        <span className="field-label">Current cycle used (hours)</span>
        <input
          className="field-input"
          type="number"
          min="0"
          max="70"
          step="0.5"
          value={values.current_cycle_used}
          placeholder="0–70"
          onChange={(e) => update('current_cycle_used', e.target.value)}
          required
          disabled={loading}
        />
        <span className="field-hint">On-duty hours already used in your 70hr / 8-day cycle.</span>
      </label>

      <button className="submit-btn" type="submit" disabled={loading}>
        {loading ? 'Planning…' : 'Plan trip'}
      </button>
    </form>
  );
}
