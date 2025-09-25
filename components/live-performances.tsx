import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Calendar, MapPin, Ticket } from "lucide-react"

export function LivePerformances() {
  const upcomingShows = [
    {
      date: "March 15, 2024",
      venue: "The Blue Note",
      location: "Nashville, TN",
      time: "8:00 PM",
      ticketUrl: "#",
    },
    {
      date: "March 22, 2024",
      venue: "Crossroads Club",
      location: "Chicago, IL",
      time: "9:00 PM",
      ticketUrl: "#",
    },
    {
      date: "April 5, 2024",
      venue: "Delta Blues Lounge",
      location: "Memphis, TN",
      time: "7:30 PM",
      ticketUrl: "#",
    },
    {
      date: "April 12, 2024",
      venue: "Bourbon Street Blues",
      location: "New Orleans, LA",
      time: "8:30 PM",
      ticketUrl: "#",
    },
  ]

  return (
    <section id="shows" className="py-20 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        <h2
          className="text-4xl md:text-5xl font-bold text-center mb-12 text-primary"
          style={{ fontFamily: "var(--font-playfair)" }}
        >
          Live Performances
        </h2>

        <div className="mb-12">
          <div className="relative w-full aspect-video max-w-3xl mx-auto rounded-lg overflow-hidden shadow-lg">
            <iframe
              width="100%"
              height="100%"
              src="https://www.youtube.com/embed/IsCnW4ynbGQ?si=GHunRzFWZdwqLLMo&start=260"
              title="YouTube video player"
              frameBorder="0"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
              referrerPolicy="strict-origin-when-cross-origin"
              allowFullScreen
              className="absolute inset-0"
            />
          </div>
        </div>

        <div className="space-y-4">
          {upcomingShows.map((show, index) => (
            null
          ))}
        </div>

        <div className="text-center mt-12">
          
          <Button
            variant="outline"
            size="lg"
            className="border-primary text-primary hover:bg-primary hover:text-primary-foreground bg-transparent w-full sm:w-auto"
          >
            Booking Inquiries
          </Button>
        </div>
      </div>
    </section>
  )
}
