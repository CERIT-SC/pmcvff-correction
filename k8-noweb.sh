#!/bin/bash

# XXX: based on magic-pipeline-web/app/pmcff/pipeline/templates/

label=pmcvff
image=ljocha/pmcvff
token=$(LC_CTYPE=C tr -cd '0-9a-z' </dev/urandom | head -c 9)
delete=0
ns=""

while getopts xi:l:t:n: opt; do case "$opt" in
	i) image=$OPTARG;;
	l) label=$OPTARG;;
	t) token=$OPTARG;;
	x) delete=1;;
	n) ns="-n $OPTARG"; nsname=$OPTARG;;
esac; done

volume=$label

if [ $delete = 1 ]; then
        kubectl delete deployment.apps/$label $ns
        kubectl delete service/$label $ns
        kubectl delete ingress.networking.k8s.io/$label $ns
        kubectl delete pvc/$label $ns
	exit 0
fi


kubectl apply $ns -f - <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: $volume
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 10Gi
  storageClassName: nfs-csi
EOF

kubectl apply $ns -f -  <<EOF
apiVersion: v1
kind: Service
metadata:
  name: $label
  labels:
    app: $label
spec:
  type: ClusterIP
  ports:
  - name: $label
    port: 80
    targetPort: 8888
  selector:
    app: $label
EOF


kubectl apply $ns -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $label
spec:
  replicas: 1
  selector:
    matchLabels:
      app: $label
  template:
    metadata:
      labels:
        app: $label
    spec:
      securityContext:
        runAsUser: 1001
        fsGroup: 1001
#      initContainers:
#        - name: shared-volume-permissions
#          image: $image
#          command: ['/bin/sh', '-c', "cp -r /work/* /shared; chown -R 1001:1001 /shared"]
#          volumeMounts:
#            - name: shared-volume
#              mountPath: /shared
      containers:
        - name: $label
          image: $image
          env:
          - name: PVC_NAME
            value: "$volume"
          - name: WORKDIR
            value: "/work"
          - name: ROOT_TMP
            value: "/var/tmp"
          - name: JUPYTER_TOKEN
            value: "$token"
          ports:
            - containerPort: 8888
          resources:
            requests:
              cpu: "200m"
            limits:
              cpu: 1
          securityContext:
      #      runAsUser: 1001
      #      runAsGroup: 1001
           # runAsNonRoot: true
            allowPrivilegeEscalation: false
          volumeMounts:
            - mountPath: /work
              name: shared-volume
          command: [ '/bin/bash', '-c', '/opt/init.sh && jupyter notebook --ip 0.0.0.0 --port 8888' ]

      volumes:
      - name: shared-volume
        persistentVolumeClaim:
          claimName: $volume
EOF

kubectl apply $ns -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: $label
  annotations:
    kuberentes.io/ingress.class: "nginx"
    kubernetes.io/tls-acme: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    external-dns.alpha.kubernetes.io/target: "k8s-public-u.cerit-sc.cz"
spec:
  tls:
    - hosts:
        - $label.dyn.cerit-sc.cz
      secretName: $label-dyn-cerit-sc-cz-tls
  rules:
  - host: $label.dyn.cerit-sc.cz
    http:
      paths:
      - backend:
          service:
            name: $label
            port:
              number: 80
        pathType: ImplementationSpecific
EOF

pod=($(kubectl get pods $ns | grep $label))
[ -z "$pod" ] && { echo Something wrong >&2; exit 1; }

echo -n Waiting for pod/${pod[0]} to start

kubectl get pods $ns | grep $label | grep Running >/dev/null
running=$?

while [ $running -ne 0 ]; do
	echo -n .
	sleep 2
	kubectl get pods $ns | grep $label | grep Running >/dev/null
	running=$?
done
echo

kubectl cp pipelineJupyter.ipynb $nsname/${pod[0]}:/work/pipelineJupyter.ipynb

echo https://$label.dyn.cerit-sc.cz/?token=$token


