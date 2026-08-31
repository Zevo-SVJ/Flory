import { Section, Eyebrow, Statement } from './section'

/**
 * FAQ.
 *
 * Native <details> — no accordion library, no client JavaScript, keyboard
 * accessible and open-by-URL friendly for free. The questions are the real
 * objections, and the answers say plainly what isn't built yet.
 */

const FAQS: Array<[string, React.ReactNode]> = [
  [
    'What can Worth analyse?',
    'Anything with a price and a link: product pages, marketplace listings, software subscriptions, online courses, digital products and services. If you can paste it, Worth will take it.',
  ],
  [
    'Does Worth work with Amazon?',
    'It’s designed to work with any retailer rather than a supported list, because the purchases people agonise over are rarely all in one shop. Worth is not a browser extension bolted onto one marketplace.',
  ],
  [
    'Can Worth analyse software and subscriptions?',
    'Yes — that’s a core case. For a subscription the questions change: what you actually use, what it costs annually versus monthly, and how hard it is to leave.',
  ],
  [
    'Can it analyse an online course?',
    'Yes, and it’s one of the places a verdict is worth the most. Courses tend to be sold on outcome claims, and Worth’s job is to check whether any of those claims are backed by something you can verify.',
  ],
  [
    'Where does Worth get its information?',
    'From retailers, review sources, seller records and price comparisons across the web. The research engine isn’t connected yet — every figure on this page is an illustrative example, and real results will cite a source for each claim.',
  ],
  [
    'How accurate is the verdict?',
    'Worth doesn’t run real analyses yet, so the honest answer is that it has no accuracy record. When it does, the evidence sits under every verdict so you can disagree with it.',
  ],
  [
    'Can I analyse a screenshot?',
    'You can upload one and it’s stored privately against your account. Reading the image isn’t built yet, so a screenshot won’t produce a verdict until the engine ships — the upload flow says so before you use it.',
  ],
  [
    'Can I cancel anytime?',
    'Yes. There’s nothing to cancel yet — billing isn’t built and there is nothing to buy — but Worth will be a straightforward monthly subscription with no lock-in.',
  ],
]

export function Faq() {
  return (
    <Section>
      <div className="grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,0.7fr)_minmax(0,1fr)] lg:gap-20">
        <div>
          <Eyebrow>Questions</Eyebrow>
          <Statement className="mt-5 max-w-[14ch]">Reasonable questions.</Statement>
        </div>

        <div className="divide-line border-line divide-y border-y">
          {FAQS.map(([question, answer]) => (
            <details key={question} className="group">
              <summary className="text-ink flex cursor-pointer list-none items-start justify-between gap-6 py-5 text-[1.0625rem] font-medium [&::-webkit-details-marker]:hidden">
                {question}
                <span
                  className="text-graphite relative mt-1.5 size-4 shrink-0 transition-transform duration-200 group-open:rotate-45 motion-reduce:transition-none"
                  aria-hidden
                >
                  <span className="absolute top-0 left-1/2 h-4 w-px -translate-x-1/2 bg-current" />
                  <span className="absolute top-1/2 left-0 h-px w-4 -translate-y-1/2 bg-current" />
                </span>
              </summary>
              <p className="text-graphite max-w-[58ch] pb-6 text-[0.9375rem] leading-relaxed">
                {answer}
              </p>
            </details>
          ))}
        </div>
      </div>
    </Section>
  )
}
