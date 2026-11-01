/**
 * A flag, written.
 *
 * The flag is a state, not a value: it is shown as a badge that says in
 * words what the colour says, so the meaning survives a reader who cannot
 * use colour and a page that is printed in black and white.
 */
import { Badge } from '@/components/ui/Badge';

export interface FlagBadgeProps {
  /** The label the product gives the flag. */
  readonly label: string;
  /** What the product set, or null when it said nothing. */
  readonly value: boolean | null;
}

export function FlagBadge({ label, value }: FlagBadgeProps) {
  if (value === null) {
    return <span className="torne-supply__flag-unknown">{label}: not established</span>;
  }
  return (
    <Badge tone={value ? 'warning' : 'neutral'} size="sm">
      {value ? label : `Not ${label.toLowerCase()}`}
    </Badge>
  );
}
