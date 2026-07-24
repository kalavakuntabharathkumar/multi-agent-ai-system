// Toaster: renders all active toasts from the useToast store into the ToastViewport.
// Placed once at the app root (in App.tsx) so toasts are always accessible.

import { useToast } from "@/hooks/use-toast"
import {
  Toast,
  ToastClose,
  ToastDescription,
  ToastProvider,
  ToastTitle,
  ToastViewport,
} from "@/components/ui/toast"

export function Toaster() {
  const { toasts } = useToast()  // subscribe to the global toast list

  return (
    <ToastProvider>
      {toasts.map(function ({ id, title, description, action, ...props }) {
        return (
          <Toast key={id} {...props}>
            <div className="grid gap-1">
              {title && <ToastTitle>{title}</ToastTitle>}
              {description && (
                <ToastDescription>{description}</ToastDescription>
              )}
            </div>
            {action}          {/* optional action button (e.g. "Undo") */}
            <ToastClose />    {/* X dismiss button */}
          </Toast>
        )
      })}
      <ToastViewport />  {/* fixed container that positions toasts on screen */}
    </ToastProvider>
  )
}
