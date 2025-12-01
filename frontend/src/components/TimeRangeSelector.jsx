import { ToggleButton, ToggleButtonGroup } from '@mui/material'

const RANGES = [
  { value: '3days', label: '3 Days' }, 
  { value: 'today', label: 'Today' },
  { value: '7days', label: '7 Days' },
  { value: '30days', label: '30 Days' },
  { value: '3months', label: '3 Months' },
  { value: '6months', label: '6 Months' },
  { value: '1year', label: '1 Year' },
]

function TimeRangeSelector({ value, onChange }) {
  return (
    <ToggleButtonGroup
      color="secondary"
      exclusive
      value={value}
      onChange={(_, newValue) => newValue && onChange(newValue)}
      size="small"
      sx={{ flexWrap: 'wrap', gap: 1 }}
    >
      {RANGES.map((range) => (
        <ToggleButton key={range.value} value={range.value} sx={{ textTransform: 'none' }}>
          {range.label}
        </ToggleButton>
      ))}
    </ToggleButtonGroup>
  )
}

export default TimeRangeSelector
