package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/alexedwards/scs/v2"
)

var sessionManager *scs.SessionManager

func main() {
	// Initialize session manager
	sessionManager = scs.New()
	sessionManager.Lifetime = 24 * time.Hour // Session expires after 24 hours
	// For production, you would typically use a persistent store like Redis or a database.
	// For now, we'll use the default in-memory store, which is not suitable for multi-instance deployments.
	// sessionManager.Store = redisstore.New(redisClient) // Example for Redis

	http.HandleFunc("/", homeHandler)
	http.HandleFunc("/set-session", setSessionHandler)
	http.HandleFunc("/get-session", getSessionHandler)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	fmt.Printf("Server starting on port %s\n", port)
	// Wrap the http.ServeMux with the session middleware
	log.Fatal(http.ListenAndServe(":"+port, sessionManager.LoadAndSave(http.DefaultServeMux)))
}

func homeHandler(w http.ResponseWriter, r *http.Request) {
	fmt.Fprintf(w, "Hello, World! This is the home page. Try /set-session and /get-session.")
}

func setSessionHandler(w http.ResponseWriter, r *http.Request) {
	sessionManager.Put(r.Context(), "message", "Hello from session!")
	sessionManager.Put(r.Context(), "userID", 123)
	fmt.Fprintf(w, "Session data set: message='Hello from session!', userID=123")
}

func getSessionHandler(w http.ResponseWriter, r *http.Request) {
	message := sessionManager.GetString(r.Context(), "message")
	userID := sessionManager.GetInt(r.Context(), "userID")
	if message == "" {
		fmt.Fprintf(w, "No session data found. Try /set-session first.")
	} else {
		fmt.Fprintf(w, "Session data retrieved: message='%s', userID=%d", message, userID)
	}
}
