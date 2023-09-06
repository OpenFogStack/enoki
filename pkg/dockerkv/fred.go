package dockerkv

import (
	"context"
	"crypto/tls"
	"crypto/x509"
	"errors"
	"fmt"
	"log"
	"os"

	fred "git.tu-berlin.de/mcc-fred/fred/proto/client"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials"
)

func createClient(host string, certFile string, keyFile string, caFiles []string) (fred.ClientClient, error) {
	serverCert, err := tls.LoadX509KeyPair(certFile, keyFile)

	if err != nil {
		return nil, err
	}

	// Create a new cert pool and add our own CA certificate
	rootCAs := x509.NewCertPool()

	for _, f := range caFiles {
		loaded, err := os.ReadFile(f)

		if err != nil {
			return nil, err
		}

		rootCAs.AppendCertsFromPEM(loaded)
	}

	config := &tls.Config{
		Certificates: []tls.Certificate{serverCert},
		ClientCAs:    rootCAs,
		RootCAs:      rootCAs,
		MinVersion:   tls.VersionTLS12,
		// TODO
		InsecureSkipVerify: true,
	}

	creds := credentials.NewTLS(config)

	conn, err := grpc.Dial(host, grpc.WithTransportCredentials(creds))

	if err != nil {
		return nil, err
	}

	return fred.NewClientClient(conn), nil
}

func getNodeID(fredClient fred.ClientClient, fredHost string) (string, error) {
	// first we need to figure out what our node is called, we only have the host
	resp, err := fredClient.GetAllReplica(context.Background(), &fred.Empty{})

	if err != nil {
		return "", err
	}

	// go through them all and figure out which one is us
	nodeID := ""
	for _, r := range resp.Replicas {
		if r.Host == fredHost {
			nodeID = r.NodeId
			break
		}
	}

	if nodeID == "" {
		return "", fmt.Errorf("could not find node id %s in %+v", fredHost, resp.Replicas)
	}

	return nodeID, nil
}

func (db *DockerKVBackend) createOrReplicateKeygroup(keygroup string) error {
	// first: check if the keygroup exists
	keygroupInfo, err := db.fredClient.GetKeygroupInfo(context.Background(), &fred.GetKeygroupInfoRequest{
		Keygroup: keygroup,
	})

	if err != nil {
		// an error! does that mean the keygroup does not exist?
		log.Println("error getting keygroup info", err)
		return db.createKeygroup(keygroup)
	}

	// the keygroup exists!
	// let's pick a replica and ask it to replicate it here
	if len(keygroupInfo.Replica) == 0 {
		return errors.New("keygroup has no replicas")
	}

	// let's first check if our node is already a replica
	for _, r := range keygroupInfo.Replica {
		if r.NodeId == db.fredNode {
			// we are already a replica, nothing to do
			log.Printf("node %s is already a replica of keygroup %s", db.fredNode, keygroup)
			return nil
		}
	}

	// let's go for the first one
	replica := keygroupInfo.Replica[0]

	// create a client to that replica
	replicaClient, err := createClient(replica.Host, db.clientCertPath, db.clientKeyPath, []string{db.caCertPath})

	if err != nil {
		log.Println("error creating replica client", err)
		return err
	}

	// ask the replica to replicate the keygroup here
	_, err = replicaClient.AddReplica(context.Background(), &fred.AddReplicaRequest{
		Keygroup: keygroup,
		NodeId:   db.fredNode,
		Expiry:   0,
	})

	if err != nil {
		log.Println("error adding replica", err)
		return err
	}

	log.Printf("successfully replicated keygroup %s to node %s", keygroup, db.fredNode)

	// we should be good to go now!
	return nil
}

func (db *DockerKVBackend) createKeygroup(keygroup string) error {
	_, err := db.fredClient.CreateKeygroup(context.Background(), &fred.CreateKeygroupRequest{
		Keygroup: keygroup,
		Mutable:  true,
		Expiry:   0,
	})

	if err != nil {
		log.Println("error creating keygroup", err)
		return fmt.Errorf("error creating keygroup: %w", err)
	}

	log.Printf("successfully created keygroup %s on node %s", keygroup, db.fredNode)

	return nil
}

func (db *DockerKVBackend) addUserToKeygroup(keygroup string, user string) error {

	log.Printf("adding user %s to keygroup %s", user, keygroup)

	for _, perm := range []fred.UserRole{
		fred.UserRole_ReadKeygroup,
		fred.UserRole_WriteKeygroup,
		fred.UserRole_ConfigureReplica,
	} {
		_, err := db.fredClient.AddUser(context.Background(), &fred.AddUserRequest{
			Keygroup: keygroup,
			User:     user,
			Role:     perm,
		})

		if err != nil {
			log.Println("error adding user to keygroup", err)
			return fmt.Errorf("error adding user to keygroup: %w", err)
		}
	}

	return nil
}
