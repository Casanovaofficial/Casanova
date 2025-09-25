import { Card, CardContent } from "@/components/ui/card"

export function AboutSection() {
  return (
    <section id="about" className="py-20 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        <h2
          className="text-4xl md:text-5xl font-bold text-center mb-12 text-primary"
          style={{ fontFamily: "var(--font-playfair)" }}
        >
          About Casanova
        </h2>

        <div className="grid md:grid-cols-2 gap-8 items-center">
          <div>
            <img
              src="https://hebbkx1anhila5yf.public.blob.vercel-storage.com/175171322_2792147431100358_3013383704014452444_n.jpg-OsK04hbwIr8iNSruqbC4HzYoSOXz1X.jpeg"
              alt="Casanova Portrait"
              className="w-full h-96 object-cover rounded-lg shadow-lg"
            />
          </div>

          <Card className="backdrop-blur-sm bg-foreground border-primary">
            <CardContent className="p-8">
              <p className="text-lg leading-relaxed mb-6 text-card">
                {
                  "From the collective energy of The Stone Avenue to the intimate expression of solo artistry, Casanova represents the natural evolution of a blues soul finding its true voice."
                }
              </p>

              <p className="text-lg leading-relaxed mb-6 text-card">
                {
                  'The journey began with shared stages and harmonized dreams, but music has a way of calling each artist toward their authentic path. What emerged is not an ending, but a transformation - from "we" to "I", from collective to personal, from band to blues storyteller.'
                }
              </p>

              <p className="text-lg leading-relaxed text-card">
                {
                  "Every chord carries the memory of collaboration while embracing the freedom of solo expression. This is Casanova - where the past informs the present, and the blues find their most honest voice."
                }
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  )
}
