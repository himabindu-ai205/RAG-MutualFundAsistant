---
name: Serene Trust
colors:
  surface: '#f7faf8'
  surface-dim: '#d7dbd9'
  surface-bright: '#f7faf8'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f1f4f3'
  surface-container: '#ebefed'
  surface-container-high: '#e5e9e7'
  surface-container-highest: '#e0e3e1'
  on-surface: '#181c1c'
  on-surface-variant: '#3e4947'
  inverse-surface: '#2d3130'
  inverse-on-surface: '#eef1f0'
  outline: '#6e7977'
  outline-variant: '#bdc9c6'
  surface-tint: '#006a63'
  primary: '#005c55'
  on-primary: '#ffffff'
  primary-container: '#0f766e'
  on-primary-container: '#a3faef'
  inverse-primary: '#80d5cb'
  secondary: '#515f74'
  on-secondary: '#ffffff'
  secondary-container: '#d5e3fc'
  on-secondary-container: '#57657a'
  tertiary: '#7f4025'
  on-tertiary: '#ffffff'
  tertiary-container: '#9c573a'
  on-tertiary-container: '#ffe5db'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#9cf2e8'
  primary-fixed-dim: '#80d5cb'
  on-primary-fixed: '#00201d'
  on-primary-fixed-variant: '#00504a'
  secondary-fixed: '#d5e3fc'
  secondary-fixed-dim: '#b9c7df'
  on-secondary-fixed: '#0d1c2e'
  on-secondary-fixed-variant: '#3a485b'
  tertiary-fixed: '#ffdbce'
  tertiary-fixed-dim: '#ffb598'
  on-tertiary-fixed: '#370e00'
  on-tertiary-fixed-variant: '#72361b'
  background: '#f7faf8'
  on-background: '#181c1c'
  surface-variant: '#e0e3e1'
typography:
  display-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 22px
    fontWeight: '600'
    lineHeight: 30px
  body-lg:
    fontFamily: Source Sans 3
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Source Sans 3
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Source Sans 3
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Source Sans 3
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  headline-md-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
  container-max: 1200px
  gutter: 20px
---

## Brand & Style
The design system is engineered to foster an atmosphere of radical transparency and calm assurance for Indian fintech users. It moves away from the aggressive, high-velocity aesthetics of trading platforms, opting instead for a "Modern Institutional" style. This aesthetic bridges the gap between the reliability of traditional official documents and the effortless usability of contemporary digital products.

The visual narrative is built on the concept of "Digital Parchment"—clean, structured information presented on warm, easy-on-the-eyes surfaces. By prioritizing high-contrast legibility and expansive whitespace, the design system minimizes cognitive load, ensuring that complex financial compliance and FAQ data feel accessible and authoritative.

## Colors
This design system utilizes a sophisticated, nature-inspired palette to evoke stability. 

- **Primary Canvas:** The seed color `#F7F4EE` serves as the global background, providing a softer, more "premium paper" feel than pure white.
- **Surface & Depth:** Pure white is reserved for interactive cards and content containers to create a clear layer of separation from the canvas.
- **Typography:** Primary text uses a near-black `#1A1A1A` for maximum accessibility. Secondary information utilizes a muted slate to maintain hierarchy without clutter.
- **Accents:** A restrained Teal-Green is the sole driver for primary actions, signifying growth and security. 
- **Compliance Tier:** High-priority notices use a sophisticated Amber/Gold. Unlike harsh red warnings, this tone feels like a curated "Important Note" in a premium ledger, using dark contrasted text for readability.

## Typography
The typographic system pairs the soft, geometric approachability of **Plus Jakarta Sans** for headings with the high-utility, humanist clarity of **Source Sans 3** for body copy.

Headlines are set with slightly tighter letter-spacing to maintain a modern editorial feel. Body text prioritizes "generous" line-heights (1.5x or higher) to ensure that long-form FAQ answers remain legible and unintimidating. For mobile devices, headlines scale down slightly to prevent awkward text wrapping while maintaining their distinct weight.

## Layout & Spacing
The layout follows a **Fixed Grid** philosophy on desktop (centered 12-column) and a fluid single-column approach on mobile. 

A strict 4px-based spacing rhythm is used to maintain mathematical harmony. To reflect the "Calm" brand pillar, the design system employs generous vertical margins (`xl`) between major sections. Content should never feel cramped; the "Safe Area" within cards is a minimum of `24px` on desktop and `16px` on mobile to ensure the hairline borders do not crowd the information.

## Elevation & Depth
Depth is achieved through a "Low-Contrast Layering" technique rather than heavy shadows.

- **Level 0 (Canvas):** The warm off-white background (`#F7F4EE`).
- **Level 1 (Cards):** Pure white surfaces featuring a `1px` hairline border in a very light grey (5% opacity black).
- **Shadows:** Use "Ambient Shadows"—extremely diffused, with a large blur radius (12px-20px) and very low opacity (0.04). The goal is to make the card feel like it is resting lightly on the paper, not floating high above it.
- **Interactions:** On hover, cards may transition to a slightly deeper shadow, but should not lift physically.

## Shapes
In alignment with the `Rounded` directive, the design system uses a base radius of `8px` (0.5rem) for small components like inputs and buttons. 

Larger containers and cards utilize `rounded-lg` (16px) to create a soft, friendly silhouette that contrasts with the serious nature of financial data. This curvature is essential to making the "Official Document" style feel modern and approachable rather than cold and bureaucratic.

## Components
- **Buttons:** Primary buttons are solid Teal-Green with white text. They use the base `8px` radius. Secondary buttons use a ghost style with a 1px slate border.
- **Cards:** The core of the FAQ experience. Cards must have a 16px radius, a hairline border, and an ambient shadow.
- **Chips/Tags:** Used for FAQ categories. These are pill-shaped (full radius) with a subtle Teal-Green tint (10% opacity) and dark Teal-Green text.
- **Input Fields:** Search bars should be large, featuring a 16px radius to match the cards, with a subtle 1px border that darkens on focus.
- **Compliance Notices (Disclaimers):** These are styled as "Note Blocks" using the Amber/Gold background. They do not use shadows; they are flat to the surface to signify they are part of the "document" layer.
- **Accordions:** FAQ items use a clean line-separator and a simple chevron icon. The active/expanded state should subtly tint the background of the question to a very pale slate or teal.