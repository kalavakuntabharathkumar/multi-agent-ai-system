// Separator UI component: renders a horizontal or vertical dividing line.
// Built on Radix Separator for correct ARIA semantics (decorative by default).

import * as React from "react"
import * as SeparatorPrimitive from "@radix-ui/react-separator"

import { cn } from "@/lib/utils"

const Separator = React.forwardRef<
  React.ElementRef<typeof SeparatorPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof SeparatorPrimitive.Root>
>(
  (
    { className, orientation = "horizontal", decorative = true, ...props },
    ref
  ) => (
    <SeparatorPrimitive.Root
      ref={ref}
      decorative={decorative}     // decorative=true hides it from screen readers
      orientation={orientation}   // "horizontal" or "vertical"
      className={cn(
        "shrink-0 bg-border",
        // Apply 1px thickness in the correct dimension based on orientation
        orientation === "horizontal" ? "h-[1px] w-full" : "h-full w-[1px]",
        className
      )}
      {...props}
    />
  )
)
Separator.displayName = SeparatorPrimitive.Root.displayName

export { Separator }
