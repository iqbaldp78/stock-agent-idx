"use client"

import * as React from "react"
import { cn } from "@/lib/cn"

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "secondary" | "destructive" | "outline" | "ghost" | "link"
  size?: "default" | "sm" | "lg" | "icon"
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => {
    const baseStyles = "inline-flex items-center justify-center whitespace-nowrap rounded-xl font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent disabled:pointer-events-none disabled:opacity-50"

    const variants = {
      default: "bg-accent text-text hover:bg-accent/90 shadow-lg shadow-accent/20",
      secondary: "bg-secondary/10 text-secondary hover:bg-secondary/20 border border-secondary/20",
      destructive: "bg-loss text-text hover:bg-loss/90 shadow-lg shadow-loss/20",
      outline: "border border-border bg-background/50 hover:bg-white/5",
      ghost: "hover:bg-white/5 text-secondary hover:text-text",
      link: "text-accent underline-offset-4 hover:underline"
    }

    const sizes = {
      default: "h-10 px-4 py-2 text-sm",
      sm: "h-9 rounded-lg px-3 text-xs",
      lg: "h-12 rounded-xl px-8 text-base",
      icon: "h-10 w-10"
    }

    return (
      <button
        className={cn(
          baseStyles,
          variants[variant],
          sizes[size],
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button }
