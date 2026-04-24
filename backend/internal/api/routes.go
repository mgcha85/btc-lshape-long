package api

import (
	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"github.com/gofiber/fiber/v2/middleware/logger"
)

func SetupRoutes(app *fiber.App, h *Handler) {
	app.Use(logger.New())
	app.Use(cors.New(cors.Config{
		AllowOrigins: "*",
		AllowHeaders: "Origin, Content-Type, Accept",
	}))

	api := app.Group("/api")

	api.Get("/health", h.HealthCheck)
	api.Get("/status", h.HealthCheck)
	api.Get("/dashboard", h.GetDashboard)
	api.Get("/stats", h.GetStats)

	api.Get("/trades", h.GetTrades)

	api.Get("/positions", h.GetPositions)

	api.Get("/settings", h.GetSettings)
	api.Post("/settings", h.UpdateSettings)

	api.Get("/strategy", h.GetStrategyConfig)
	api.Post("/strategy", h.UpdateStrategyConfig)

	api.Post("/trading/toggle", h.ToggleTrading)

	app.Static("/", "./web/dist")
}
