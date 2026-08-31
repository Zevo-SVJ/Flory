import Image from 'next/image'
import { PRODUCT_ASSETS, type ProductAssetKey } from '@/lib/product-assets'
import { cn } from '@/lib/utils/cn'

/**
 * Renders a product from the asset manifest.
 *
 * Handles both locally authored renders and real photographs, so dropping a
 * real photo into `lib/product-assets.ts` needs no change here: renders are
 * contained (they carry their own negative space), photographs are covered.
 */
export function ProductImage({
  asset,
  className,
  imageClassName,
  priority = false,
  sizes = '(max-width: 640px) 60vw, 320px',
}: {
  asset: ProductAssetKey
  className?: string
  imageClassName?: string
  priority?: boolean
  sizes?: string
}) {
  const item = PRODUCT_ASSETS[asset]

  return (
    <div className={cn('relative', className)}>
      <Image
        src={item.src}
        alt={item.alt}
        width={item.width}
        height={item.height}
        priority={priority}
        sizes={sizes}
        className={cn(
          'h-full w-full',
          item.kind === 'photo' ? 'object-cover' : 'object-contain',
          imageClassName,
        )}
      />
    </div>
  )
}
