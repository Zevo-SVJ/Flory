import { Section, Beat } from './section'
import { EvidenceModule, Finding } from '@/components/worth/evidence-module'
import { PriceDrop } from '@/components/worth/price-drop'
import { EVIDENCE_WALL } from '@/lib/analysis/fixtures'

/**
 * What Worth checks — shown as the findings themselves.
 *
 * Six evidence modules holding the actual output of each dimension, not six
 * icons describing a capability. The asymmetric spans stop the wall reading as
 * a feature grid: price and reviews carry the most weight and take the most
 * room, exactly as they do in the verdict.
 */
export function EvidenceWall() {
  return (
    <Section>
      <div className="flex flex-col gap-3">
        <Beat index="03">Worth checks</Beat>
        <h2 className="text-statement text-ink max-w-[24ch] font-serif font-medium">
          Six questions. Answered with what it found.
        </h2>
      </div>

      <div className="mt-10 grid grid-cols-1 gap-3 sm:mt-14 sm:grid-cols-2 lg:grid-cols-3">
        <EvidenceModule
          label="Price"
          count={`${EVIDENCE_WALL.retailersChecked} retailers`}
          tone="brand"
          className="sm:col-span-2"
        >
          <PriceDrop
            from={EVIDENCE_WALL.priceListed}
            to={EVIDENCE_WALL.priceFound}
            saving="€70"
            size="sm"
          />
        </EvidenceModule>

        <EvidenceModule label="Value">
          <ul className="flex flex-col gap-1.5 text-[0.875rem]">
            <Row k="Noise cancelling" v="Best in class" tone="buy" />
            <Row k="Battery" v="30 h" tone="buy" />
            <Row k="Case" v="Bulkier than before" tone="think" />
          </ul>
        </EvidenceModule>

        <EvidenceModule
          label="Reviews"
          count={`${EVIDENCE_WALL.reviewsRead.toLocaleString('en-IE')} read`}
          className="sm:col-span-2"
        >
          <div className="flex flex-col gap-2.5">
            <blockquote className="border-buy/40 text-ink border-l-2 pl-3 font-serif text-[0.9375rem] leading-snug">
              {EVIDENCE_WALL.reviewPositive}
            </blockquote>
            <blockquote className="border-think/40 text-ink-soft border-l-2 pl-3 font-serif text-[0.9375rem] leading-snug">
              {EVIDENCE_WALL.reviewNegative}
            </blockquote>
          </div>
        </EvidenceModule>

        <EvidenceModule label="Trust" tone="positive">
          <ul className="flex flex-col gap-1.5">
            <Finding>Authorised seller</Finding>
            <Finding>{EVIDENCE_WALL.sellerReturns}</Finding>
            <Finding>{EVIDENCE_WALL.sellerWarranty}</Finding>
          </ul>
        </EvidenceModule>

        <EvidenceModule label="Risk" tone="caution">
          <ul className="flex flex-col gap-1.5">
            <Finding tone="caution">{EVIDENCE_WALL.riskNote}</Finding>
          </ul>
        </EvidenceModule>

        <EvidenceModule
          label="Alternatives"
          tone="positive"
          className="sm:col-span-2 lg:col-span-2"
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="min-w-0">
              <p className="text-ink text-[0.9375rem] font-medium">
                Same model, authorised retailer
              </p>
              <p className="text-graphite text-[0.875rem]">Identical warranty and returns</p>
            </div>
            <span className="tnum text-buy text-2xl font-semibold">€329</span>
          </div>
        </EvidenceModule>
      </div>

      <p className="text-faint mt-5 text-[0.75rem]">
        Illustrative evidence. Real analyses will cite a source for every line.
      </p>
    </Section>
  )
}

function Row({ k, v, tone }: { k: string; v: string; tone: 'buy' | 'think' }) {
  return (
    <li className="flex justify-between gap-3">
      <span className="text-graphite">{k}</span>
      <span className={tone === 'buy' ? 'text-buy font-medium' : 'text-think font-medium'}>
        {v}
      </span>
    </li>
  )
}
