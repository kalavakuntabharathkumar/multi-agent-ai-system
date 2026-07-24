// Skeleton UI component: animated loading placeholder for content that hasn't loaded yet.
// Renders a pulsing rounded rectangle matching the size of its container.

import { cn } from "@/lib/utils"

function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-primary/10", className)}  // pulse animation signals loading state
      {...props}
    />
  )
}

export { Skeleton }
