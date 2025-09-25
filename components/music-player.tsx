"use client"

import { useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Play, Pause, SkipBack, SkipForward, Volume2 } from "lucide-react"
import { Slider } from "@/components/ui/slider"

export function MusicPlayer() {
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTrack, setCurrentTrack] = useState(0)

  const tracks = [
    { title: "Swamp Face", duration: "00:00", artist: "Casanova" },
    { title: "Lonely Highway", duration: "3:45", artist: "Casanova" },
    { title: "Soul Revival", duration: "5:12", artist: "Casanova" },
    { title: "Electric Dreams", duration: "4:01", artist: "Casanova" },
    { title: "Delta Sunrise", duration: "3:58", artist: "Casanova" },
  ]

  return (
    <section id="music" className="py-20 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        <h2
          className="text-4xl md:text-5xl font-bold text-center mb-12 text-primary"
          style={{ fontFamily: "var(--font-playfair)" }}
        >
          Track List
        </h2>

        <Card className="backdrop-blur-sm shadow bg-foreground text-primary border-primary">
          <CardContent className="p-4 sm:p-6 text-primary bg-foreground">
            {/* Album Art and Current Track Info */}
            <div className="flex flex-col md:flex-row gap-4 sm:gap-6 mb-6">
              <div className="flex-shrink-0">
                <img
                  src="https://hebbkx1anhila5yf.public.blob.vercel-storage.com/design-mode-images/297600946_3146056292376135_8652925415428182523_n.jpg-4vBSavW4Ol6dgu5WU6OMSMVV8AAvhJ.jpeg"
                  alt="Current Album"
                  className="w-32 h-32 sm:w-48 sm:h-48 mx-auto md:mx-0 rounded-lg shadow-lg"
                />
              </div>
              <div className="flex-1 text-center md:text-left">
                <h3 className="text-xl sm:text-2xl font-bold mb-2 text-popover-foreground">
                  {tracks[currentTrack].title}
                </h3>
                <p className="mb-4 text-primary">by {tracks[currentTrack].artist}</p>

                {/* Player Controls */}
                <div className="flex items-center justify-center md:justify-start gap-2 sm:gap-4 mb-4">
                  <Button variant="ghost" size="sm">
                    <SkipBack className="h-4 w-4 sm:h-5 sm:w-5" />
                  </Button>
                  <Button size="lg" className="bg-primary hover:bg-primary/90" onClick={() => setIsPlaying(!isPlaying)}>
                    {isPlaying ? (
                      <Pause className="h-5 w-5 sm:h-6 sm:w-6" />
                    ) : (
                      <Play className="h-5 w-5 sm:h-6 sm:w-6" />
                    )}
                  </Button>
                  <Button variant="ghost" size="sm">
                    <SkipForward className="h-4 w-4 sm:h-5 sm:w-5" />
                  </Button>
                </div>

                {/* Progress Bar */}
                <div className="flex items-center gap-2 mb-4">
                  <span className="text-xs sm:text-sm text-muted-foreground">1:23</span>
                  <Slider defaultValue={[33]} max={100} step={1} className="flex-1" />
                  <span className="text-xs sm:text-sm text-muted-foreground">{tracks[currentTrack].duration}</span>
                </div>

                {/* Volume Control */}
                <div className="flex items-center gap-2 max-w-24 sm:max-w-32 mx-auto md:mx-0">
                  <Volume2 className="h-3 w-3 sm:h-4 sm:w-4 text-muted-foreground" />
                  <Slider defaultValue={[75]} max={100} step={1} />
                </div>
              </div>
            </div>

            {/* Track List */}
            <div className="space-y-2">
              {tracks.map((track, index) => (
                <div
                  key={index}
                  className={`flex items-center justify-between p-2 sm:p-3 rounded-lg cursor-pointer transition-colors ${
                    index === currentTrack ? "bg-primary/10 text-primary" : "hover:bg-muted/50 text-foreground"
                  }`}
                  onClick={() => setCurrentTrack(index)}
                >
                  <div className="flex items-center gap-2 sm:gap-3">
                    <span className="text-xs sm:text-sm font-medium w-4 sm:w-6">{index + 1}</span>
                    <div>
                      <p className="text-sm sm:text-base font-medium text-primary">{track.title}</p>
                      <p className="text-xs sm:text-sm text-card">{track.artist}</p>
                    </div>
                  </div>
                  <span className="text-xs sm:text-sm text-muted-foreground">{track.duration}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </section>
  )
}
